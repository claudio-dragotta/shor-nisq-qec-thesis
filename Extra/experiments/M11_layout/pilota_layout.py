"""M11: correlazione tra score di calibrazione e successo di Shor per layout diversi.

Il backend e' una snapshot offline di IBM Sherbrooke. ``InstructionProperties.error`` viene
interpretato come *average gate infidelity* complessiva e trasformato in un canale
depolarizzante con la stessa infedelta'. T1/T2 non vengono aggiunti separatamente: il loro
effetto e' gia' incluso nella calibrazione del gate e questo esperimento non pretende quindi
di stimare un contributo T1/T2 distinto.

Il coupling usato dal transpiler conserva la direzione nativa degli ECR. Ogni circuito viene
controllato dopo la compilazione: un ECR privo della corrispondente calibrazione e' un errore
bloccante, non un gate silenziosamente ideale.
"""

import argparse
import hashlib
import json
import os
import random
import sys
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np
from qiskit import transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke
from scipy.stats import spearmanr

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'campagne_classiche_M1-M4'))
from shor_core import (                                      # noqa: E402
    experiment_manifest,
    extract_factors,
    shor_circuit,
)

N, A, N_COUNT = 15, 7, 8
N_QUBITS = N_COUNT + 4
BASIS = ['sx', 'rz', 'x', 'ecr']
NOISE_MODEL_REVISION = 'm11-target-agi-depolarizing-only-v2'


def _as_float(value):
    return None if value is None else float(value)


def package_versions():
    """Versioni necessarie per riprodurre backend, transpiler e simulatore."""
    out = {}
    for package in ('qiskit', 'qiskit-aer', 'qiskit-ibm-runtime', 'numpy', 'scipy'):
        try:
            out[package] = version(package)
        except PackageNotFoundError:
            out[package] = None
    return out


# --------------------------------------------------------------------- calibrazione
def leggi_calibrazione(backend):
    """Estrae solo le quantita' effettivamente usate dal modello M11."""
    target = backend.target
    cal = {
        'readout': {},
        'sx_err': {}, 'sx_dur': {},
        'x_err': {}, 'x_dur': {},
        'ecr': {}, 'ecr_dur': {},
    }
    for q in range(backend.num_qubits):
        measure = target['measure'].get((q,))
        cal['readout'][q] = (
            float(measure.error)
            if measure is not None and measure.error is not None else 0.0
        )

        sx = target['sx'].get((q,))
        sx_error = float(sx.error) if sx is not None and sx.error is not None else 0.0
        sx_duration = _as_float(sx.duration) if sx is not None else None
        cal['sx_err'][q] = sx_error
        cal['sx_dur'][q] = sx_duration

        x = target['x'].get((q,))
        # Il fallback resta separato e viene registrato nel manifest tramite i valori estratti.
        cal['x_err'][q] = (
            float(x.error) if x is not None and x.error is not None
            else 1.0 - (1.0 - sx_error) ** 2
        )
        cal['x_dur'][q] = (
            _as_float(x.duration) if x is not None and x.duration is not None
            else (2.0 * sx_duration if sx_duration is not None else None)
        )

    for (a, b), props in target['ecr'].items():
        if props is not None and props.error is not None:
            edge = (int(a), int(b))
            cal['ecr'][edge] = float(props.error)
            cal['ecr_dur'][edge] = _as_float(props.duration)
    return cal


def calibration_payload(cal):
    """Forma JSON canonica: evita chiavi tuple e dipendenza dall'ordine dei dict."""
    return {
        'readout': [[q, cal['readout'][q]] for q in sorted(cal['readout'])],
        'sx': [[q, cal['sx_err'][q], cal['sx_dur'][q]] for q in sorted(cal['sx_err'])],
        'x': [[q, cal['x_err'][q], cal['x_dur'][q]] for q in sorted(cal['x_err'])],
        'ecr': [[a, b, cal['ecr'][(a, b)], cal['ecr_dur'].get((a, b))]
                for a, b in sorted(cal['ecr'])],
    }


def calibration_hash(cal):
    raw = json.dumps(calibration_payload(cal), sort_keys=True, separators=(',', ':'),
                     allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def coupling_non_orientata(cal):
    """Adiacenza non orientata usata esclusivamente per campionare sottografi connessi."""
    adj = {}
    for a, b in cal['ecr']:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    return adj


# --------------------------------------------------------------------- layout
def campiona_layout(adj, k, n_qubit, rng):
    """Campiona sottografi connessi per crescita casuale (non uniformemente)."""
    nodi = sorted(adj)
    visti, out = set(), []
    tentativi = 0
    while len(out) < k and tentativi < k * 200:
        tentativi += 1
        start = rng.choice(nodi)
        scelti = [start]
        frontiera = set(adj[start])
        while len(scelti) < n_qubit and frontiera:
            q = rng.choice(sorted(frontiera))
            scelti.append(q)
            frontiera |= adj[q]
            frontiera -= set(scelti)
        if len(scelti) < n_qubit:
            continue
        chiave = tuple(sorted(scelti))
        if chiave in visti:
            continue
        visti.add(chiave)
        out.append(scelti)
    return out


def coupling_ridotta(layout, cal):
    """Soli archi ECR diretti e calibrati, rietichettati 0..n-1."""
    idx = {q: i for i, q in enumerate(layout)}
    return [[idx[a], idx[b]] for a, b in cal['ecr'] if a in idx and b in idx]


def ecr_fisici(tqc, layout):
    """Restituisce, nell'ordine del circuito, gli ECR tradotti ai qubit della snapshot."""
    edges = []
    for inst in tqc.data:
        if inst.operation.name != 'ecr':
            continue
        a = tqc.find_bit(inst.qubits[0]).index
        b = tqc.find_bit(inst.qubits[1]).index
        if a >= len(layout) or b >= len(layout):
            raise AssertionError(f'ECR su indice fuori layout: {(a, b)}')
        edges.append((layout[a], layout[b]))
    return edges


def assert_ecr_calibrati(tqc, layout, cal):
    """Blocca circuiti contenenti direzioni ECR non native o non rumorose."""
    mancanti = sorted({edge for edge in ecr_fisici(tqc, layout) if edge not in cal['ecr']})
    if mancanti:
        raise AssertionError(f'ECR senza calibrazione diretta: {mancanti}')


# --------------------------------------------------------------------- rumore
def depolarizing_from_average_error(error, n_qubits):
    """Canale depolarizzante con average gate infidelity uguale a ``error``."""
    error = float(error)
    dim = 2 ** n_qubits
    max_error = dim / (dim + 1)
    if not 0.0 <= error <= max_error:
        raise ValueError(f'Average gate infidelity fuori dominio: {error}')
    if error == 0.0:
        return None
    depol_lambda = dim * error / (dim - 1)
    return depolarizing_error(depol_lambda, n_qubits)


def noise_model_layout(layout, cal):
    """Modello calibrato depolarizing-only; nessuna aggiunta separata di T1/T2."""
    nm = NoiseModel(basis_gates=BASIS)
    idx = {q: i for i, q in enumerate(layout)}
    for q, i in idx.items():
        for gate, errors in (('sx', cal['sx_err']), ('x', cal['x_err'])):
            err = depolarizing_from_average_error(errors[q], 1)
            if err is not None:
                nm.add_quantum_error(err, gate, [i])
        p = float(cal['readout'][q])
        if not 0.0 <= p <= 0.5:
            raise ValueError(f'Errore readout simmetrico fuori dominio per q={q}: {p}')
        if p:
            # La Target espone un solo errore medio: il modello simmetrico e' esplicito.
            nm.add_readout_error(ReadoutError([[1 - p, p], [p, 1 - p]]), [i])
    for (a, b), average_error in cal['ecr'].items():
        if a not in idx or b not in idx:
            continue
        err = depolarizing_from_average_error(average_error, 2)
        if err is not None:
            nm.add_quantum_error(err, 'ecr', [idx[a], idx[b]])
    return nm


# --------------------------------------------------------------------- punteggio fedelta'
def punteggio_fedelta(tqc, layout, cal):
    """Score mapomatic-like basato sugli stessi errori target usati dal simulatore."""
    idx_inv = {i: q for i, q in enumerate(layout)}
    log_fidelity = 0.0
    for inst in tqc.data:
        nome = inst.operation.name
        qs = [idx_inv[tqc.find_bit(q).index] for q in inst.qubits]
        if nome == 'ecr' and len(qs) == 2:
            edge = (qs[0], qs[1])
            if edge not in cal['ecr']:
                raise AssertionError(f'ECR senza calibrazione diretta nello score: {edge}')
            error = cal['ecr'][edge]
        elif nome == 'sx':
            error = cal['sx_err'][qs[0]]
        elif nome == 'x':
            error = cal['x_err'][qs[0]]
        elif nome == 'measure':
            error = cal['readout'][qs[0]]
        else:
            continue
        error = min(max(float(error), 0.0), 1.0)
        if error >= 1.0:
            return 1.0
        log_fidelity += np.log1p(-error)
    return float(1.0 - np.exp(log_fidelity))


# --------------------------------------------------------------------- simulazione e statistiche
def _conta_successi(counts):
    successi = 0
    totale = sum(counts.values())
    for bit, n in counts.items():
        value = int(bit.replace(' ', ''), 2)
        if extract_factors(value, N_COUNT, N, A)[0] is not None:
            successi += n
    return int(successi), int(totale)


def prob_successo(tqc, nm, shots, seed):
    sim = AerSimulator(noise_model=nm, method='statevector')
    counts = sim.run(tqc, shots=shots, seed_simulator=int(seed)).result().get_counts()
    successi, totale = _conta_successi(counts)
    return successi / totale


def seed_schedule(seed, n, stream=0):
    """Calendario uint32 deterministico; lo stesso calendario e' riusabile tra layout."""
    if n <= 0:
        raise ValueError('n deve essere positivo')
    sequence = np.random.SeedSequence([int(seed), int(stream)])
    return [int(x) for x in sequence.generate_state(n, dtype=np.uint32)]


def split_shots(shots, batches):
    if batches < 2:
        raise ValueError('Servono almeno due batch per train/holdout')
    if shots < batches:
        raise ValueError('shots deve essere almeno uguale al numero di batch')
    base, remainder = divmod(int(shots), int(batches))
    return [base + (i < remainder) for i in range(batches)]


def run_success_batches(tqc, nm, shot_schedule, seeds, n_train):
    if len(shot_schedule) != len(seeds):
        raise ValueError('shot_schedule e seeds devono avere la stessa lunghezza')
    if not 0 < n_train < len(seeds):
        raise ValueError('n_train deve lasciare almeno un batch holdout')
    sim = AerSimulator(noise_model=nm, method='statevector')
    rows = []
    for index, (shots, seed) in enumerate(zip(shot_schedule, seeds)):
        counts = sim.run(tqc, shots=int(shots), seed_simulator=int(seed)).result().get_counts()
        successi, totale = _conta_successi(counts)
        rows.append({
            'batch': index,
            'partition': 'train' if index < n_train else 'holdout',
            'seed_simulator': int(seed),
            'shots': totale,
            'successes': successi,
            'P_success': successi / totale,
        })
    return rows


def summarize_batches(rows, partition=None):
    selected = [r for r in rows if partition is None or r['partition'] == partition]
    if not selected:
        raise ValueError(f'Nessun batch per partition={partition!r}')
    successes = sum(r['successes'] for r in selected)
    shots = sum(r['shots'] for r in selected)
    probability = successes / shots
    se = (probability * (1.0 - probability) / shots) ** 0.5
    return {'P_success': float(probability), 'P_success_se': float(se),
            'successes': int(successes), 'shots': int(shots), 'n_batches': len(selected)}


def safe_spearman(x, y):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if len(x) < 2 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return None
    value = float(spearmanr(x, y).statistic)
    return value if np.isfinite(value) else None


def bootstrap_spearman_ci(x, y, seed, n_bootstrap=2000, confidence=0.95):
    """Bootstrap sui layout; ``spearmanr`` gestisce correttamente i pareggi."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    estimate = safe_spearman(x, y)
    if estimate is None or n_bootstrap <= 0:
        return {'estimate': estimate, 'ci_low': None, 'ci_high': None, 'n_valid': 0}
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(int(n_bootstrap)):
        idx = rng.integers(0, len(x), size=len(x))
        value = safe_spearman(x[idx], y[idx])
        if value is not None:
            values.append(value)
    if not values:
        return {'estimate': estimate, 'ci_low': None, 'ci_high': None, 'n_valid': 0}
    alpha = (1.0 - confidence) / 2.0
    low, high = np.quantile(values, [alpha, 1.0 - alpha])
    return {'estimate': estimate, 'ci_low': float(low), 'ci_high': float(high),
            'n_valid': len(values), 'confidence': confidence}


def _validate_args(args):
    if args.layouts < 5:
        raise ValueError('--layouts deve essere almeno 5 per una correlazione interpretabile')
    if not 0.0 < args.holdout_fraction < 1.0:
        raise ValueError('--holdout-fraction deve essere tra 0 e 1')
    if args.bootstrap < 0:
        raise ValueError('--bootstrap non puo essere negativo')
    split_shots(args.shots, args.batches)


def main():
    parser = argparse.ArgumentParser(description="M11 — score di calibrazione vs successo")
    parser.add_argument('--layouts', type=int, default=60)
    parser.add_argument('--shots', type=int, default=8192,
                        help='shot totali per layout, ripartiti fra i batch')
    parser.add_argument('--batches', type=int, default=8)
    parser.add_argument('--holdout-fraction', type=float, default=0.5)
    parser.add_argument('--bootstrap', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output-dir', type=Path, default=Path('.'))
    args = parser.parse_args()
    _validate_args(args)

    rng = random.Random(args.seed)
    backend = FakeSherbrooke()
    cal = leggi_calibrazione(backend)
    adj = coupling_non_orientata(cal)
    cal_hash = calibration_hash(cal)
    print(f"Backend snapshot: {backend.name} ({backend.num_qubits} qubit)")
    print(f"Noise model: {NOISE_MODEL_REVISION}; nessuna aggiunta separata T1/T2")

    layouts = campiona_layout(adj, args.layouts, N_QUBITS, rng)
    print(f"Sottografi random-growth: {len(layouts)} da {N_QUBITS} qubit\n")
    if len(layouts) < args.layouts:
        raise RuntimeError(f'Richiesti {args.layouts} layout, ottenuti solo {len(layouts)}')

    shot_schedule = split_shots(args.shots, args.batches)
    simulator_seeds = seed_schedule(args.seed, args.batches, stream=11)
    n_holdout = max(1, round(args.batches * args.holdout_fraction))
    n_train = args.batches - n_holdout
    if n_train < 1:
        raise ValueError('La frazione holdout non lascia batch di train')

    qc = shor_circuit(N, A, N_COUNT)
    righe, fallimenti = [], []
    print("  #   qubit fisici (primi 6)   score_calib   P_holdout   ECR")
    print("  " + "-" * 68)
    for index, layout in enumerate(layouts):
        coupling = coupling_ridotta(layout, cal)
        try:
            tqc = transpile(qc, basis_gates=BASIS, coupling_map=coupling,
                            optimization_level=3, seed_transpiler=args.seed)
            assert_ecr_calibrati(tqc, layout, cal)
            score = punteggio_fedelta(tqc, layout, cal)
            noise_model = noise_model_layout(layout, cal)
            batches = run_success_batches(
                tqc, noise_model, shot_schedule, simulator_seeds, n_train
            )
        except Exception as exc:
            fallimenti.append({'layout_id': index, 'layout': layout,
                               'error_type': type(exc).__name__, 'message': str(exc)})
            print(f"  {index:<3} fallita: {type(exc).__name__}: {exc}")
            continue

        train = summarize_batches(batches, 'train')
        holdout = summarize_batches(batches, 'holdout')
        overall = summarize_batches(batches)
        necr = int(tqc.count_ops().get('ecr', 0))
        righe.append({
            'layout_id': index,
            'layout': [int(q) for q in layout],
            'punteggio_fedelta': score,
            'P_success': overall['P_success'],
            'P_success_se': overall['P_success_se'],
            'train': train,
            'holdout': holdout,
            'n_ecr': necr,
            'depth': int(tqc.depth()),
            'operations': {name: int(count) for name, count in tqc.count_ops().items()},
            'batches': batches,
        })
        print(f"  {index:<3} {str(layout[:6]):<24} {score:.6f}      "
              f"{holdout['P_success']:.4f}      {necr}", flush=True)

    if len(righe) < 5:
        raise RuntimeError('Meno di cinque layout validi: impossibile concludere')

    score = np.array([r['punteggio_fedelta'] for r in righe])
    p_train = np.array([r['train']['P_success'] for r in righe])
    p_holdout = np.array([r['holdout']['P_success'] for r in righe])
    spearman = bootstrap_spearman_ci(
        score, p_holdout,
        seed=seed_schedule(args.seed, 1, stream=12)[0],
        n_bootstrap=args.bootstrap,
    )
    pearson = (float(np.corrcoef(score, p_holdout)[0, 1])
               if np.ptp(score) and np.ptp(p_holdout) else None)

    fidelity_index = int(np.argmin(score))
    selected_index = int(np.argmax(p_train))
    holdout_fidelity = float(p_holdout[fidelity_index])
    holdout_selected = float(p_holdout[selected_index])
    holdout_loss = holdout_selected - holdout_fidelity

    print("\n" + "=" * 74)
    print("ESITO M11 — valutazione holdout")
    print("=" * 74)
    print(f"  layout validi                         : {len(righe)}")
    print(f"  Spearman score vs P_holdout           : {spearman['estimate']}")
    print(f"  CI bootstrap                          : "
          f"[{spearman['ci_low']}, {spearman['ci_high']}]")
    print(f"  P_holdout layout scelto dalla fedelta': {holdout_fidelity:.4f}")
    print(f"  P_holdout layout scelto sul train     : {holdout_selected:.4f}")
    print(f"  differenza holdout                     : {holdout_loss:+.4f}")
    print("  Nota: il campionamento random-growth non e' uniforme; risultato esplorativo.")

    timestamp = datetime.now().astimezone()
    out = {
        'schema_version': '2.0',
        'milestone': 'M11_pilota_layout',
        'timestamp': timestamp.isoformat(),
        'seed': args.seed,
        'backend': {
            'name': backend.name,
            'class': type(backend).__name__,
            'num_qubits': int(backend.num_qubits),
            'calibration_sha256': cal_hash,
        },
        'software_versions': package_versions(),
        'manifest': experiment_manifest(N, A, N_COUNT),
        'noise_model': {
            'revision': NOISE_MODEL_REVISION,
            'description': ('target.error converted from average gate infidelity to a '
                            'depolarizing channel; symmetric readout; no separate T1/T2'),
            'rz_virtual': True,
            'ecr_directional': True,
        },
        'design': {
            'layout_sampling': 'connected random-growth; not uniform',
            'requested_layouts': args.layouts,
            'valid_layouts': len(righe),
            'shots_per_layout': args.shots,
            'batch_shots': shot_schedule,
            'n_train_batches': n_train,
            'n_holdout_batches': args.batches - n_train,
            'common_simulator_seeds': simulator_seeds,
            'common_seed_transpiler': args.seed,
            'basis_gates': BASIS,
            'optimization_level': 3,
            'bootstrap_resamples': args.bootstrap,
        },
        'statistics': {
            'pearson_score_vs_holdout': pearson,
            'spearman_score_vs_holdout': spearman,
            'selected_by_fidelity_layout_id': righe[fidelity_index]['layout_id'],
            'selected_on_train_layout_id': righe[selected_index]['layout_id'],
            'P_holdout_selected_by_fidelity': holdout_fidelity,
            'P_holdout_selected_on_train': holdout_selected,
            'holdout_difference_train_selection_minus_fidelity': holdout_loss,
            'interpretation': ('exploratory association on a non-uniform random-growth sample; '
                               'selection evaluated on disjoint holdout batches'),
        },
        'failures': fallimenti,
        'points': righe,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    filename = args.output_dir / f"results_M11_pilota_v2_{timestamp:%Y%m%d_%H%M%S}.json"
    with filename.open('w', encoding='utf-8') as stream:
        json.dump(out, stream, indent=2, ensure_ascii=False, allow_nan=False)
    print(f"\nRisultati salvati in: {filename}")


if __name__ == '__main__':
    main()
