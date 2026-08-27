"""M11b: associazione fra readout effettivo dopo routing e successo di Shor.

Le strategie di ``initial_layout`` servono a generare variazione entro lo stesso sottografo,
ma non vengono interpretate come trattamenti causali: il routing puo' spostare il registro di
conteggio. L'esposizione osservata e' quindi il readout dei qubit fisici effettivamente
misurati; l'analisi controlla per ECR, profondita' e sottografo.
"""

import argparse
import gc
import json
import random
from datetime import datetime
from pathlib import Path

import numpy as np
from qiskit import transpile
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke

import analisi_ruoli as AR
import pilota_layout as P

N_COUNT = P.N_COUNT
N_WORK = 4
CHECKPOINT_NAME = 'checkpoint_M11b_ruoli_v2.json'


def _write_json_atomic(path, payload):
    """Scrive un JSON senza lasciare checkpoint parziali in caso di arresto."""
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False, allow_nan=False)
    temporary.replace(path)


def _checkpoint_signature(args, backend, cal):
    return {
        'requested_subgraphs': int(args.sottografi),
        'shots_per_strategy': int(args.shots),
        'batches': int(args.batches),
        'holdout_fraction': float(args.holdout_fraction),
        'seed': int(args.seed),
        'random_initial_layouts_per_subgraph': int(args.casuali),
        'backend_name': backend.name,
        'calibration_sha256': P.calibration_hash(cal),
        'noise_model_revision': P.NOISE_MODEL_REVISION,
    }


def _load_checkpoint(path, signature, subgraphs):
    if not path.exists():
        return [], []
    payload = json.loads(path.read_text(encoding='utf-8'))
    if (payload.get('schema_version') != '2.0' or
            payload.get('milestone') != 'M11b_ruoli_checkpoint'):
        raise ValueError(f'Checkpoint M11b incompatibile: {path}')
    if payload.get('signature') != signature:
        raise ValueError(
            f'Checkpoint M11b riferito a una configurazione diversa: {path}'
        )
    rows = payload.get('righe', [])
    expected = [[int(q) for q in layout] for layout in subgraphs]
    for row in rows:
        index = int(row['subgraph_id'])
        if index >= len(expected) or row.get('sottografo') != expected[index]:
            raise ValueError(f'Checkpoint M11b con sottografi incompatibili: {path}')
    return rows, payload.get('failures', [])


def _save_checkpoint(path, signature, rows, failures, status='in_progress', result=None):
    payload = {
        'schema_version': '2.0',
        'milestone': 'M11b_ruoli_checkpoint',
        'status': status,
        'updated_at': datetime.now().astimezone().isoformat(),
        'signature': signature,
        'failures': failures,
        'righe': rows,
    }
    if result is not None:
        payload['result'] = str(Path(result).resolve())
    _write_json_atomic(path, payload)


def qubit_fisici_misurati(tqc, layout):
    """Qubit della snapshot sui quali cadono realmente le misure dopo il routing."""
    measured = []
    for inst in tqc.data:
        if inst.operation.name != 'measure':
            continue
        reduced_index = tqc.find_bit(inst.qubits[0]).index
        if reduced_index >= len(layout):
            raise AssertionError(f'Misura su indice fuori layout: {reduced_index}')
        measured.append(int(layout[reduced_index]))
    return measured


def readout_dei_misurati(tqc, layout, cal):
    measured = qubit_fisici_misurati(tqc, layout)
    if not measured:
        raise AssertionError('Il circuito compilato non contiene misure')
    return float(np.mean([cal['readout'][q] for q in measured]))


def strategie_iniziali(layout, cal, casuali, rng):
    """Initial layout descrittivi; i nomi non implicano la collocazione finale."""
    ordine = sorted(range(len(layout)), key=lambda i: cal['readout'][layout[i]])
    strategies = {}

    low_readout = [0] * len(layout)
    for virtual, physical in enumerate(ordine[:N_COUNT]):
        low_readout[virtual] = physical
    for offset, physical in enumerate(ordine[N_COUNT:]):
        low_readout[N_COUNT + offset] = physical
    strategies['init-readout-basso'] = low_readout

    high_readout = [0] * len(layout)
    for virtual, physical in enumerate(ordine[N_WORK:]):
        high_readout[virtual] = physical
    for offset, physical in enumerate(ordine[:N_WORK]):
        high_readout[N_COUNT + offset] = physical
    strategies['init-readout-alto'] = high_readout

    strategies['transpiler'] = None
    for index in range(casuali):
        permutation = list(range(len(layout)))
        rng.shuffle(permutation)
        strategies[f'casuale-{index + 1}'] = permutation
    return strategies


def valuta(qc, layout, coupling, cal, initial_layout, shot_schedule,
           simulator_seeds, n_train, transpiler_seed):
    tqc = transpile(
        qc,
        basis_gates=P.BASIS,
        coupling_map=coupling,
        optimization_level=2,
        initial_layout=initial_layout,
        seed_transpiler=int(transpiler_seed),
    )
    P.assert_ecr_calibrati(tqc, layout, cal)
    noise_model = P.noise_model_layout(layout, cal)
    batches = P.run_success_batches(
        tqc, noise_model, shot_schedule, simulator_seeds, n_train
    )
    measured = qubit_fisici_misurati(tqc, layout)
    readout = float(np.mean([cal['readout'][q] for q in measured]))
    overall = P.summarize_batches(batches)
    train = P.summarize_batches(batches, 'train')
    holdout = P.summarize_batches(batches, 'holdout')
    return {
        'P_success': overall['P_success'],
        'P_success_se': overall['P_success_se'],
        'train': train,
        'holdout': holdout,
        'readout_misurati': readout,
        'qubit_fisici_misurati': measured,
        'n_ecr': int(tqc.count_ops().get('ecr', 0)),
        'depth': int(tqc.depth()),
        'operations': {name: int(count) for name, count in tqc.count_ops().items()},
        'batches': batches,
    }


def _validate_args(args):
    if args.sottografi < 2:
        raise ValueError('--sottografi deve essere almeno 2')
    if args.casuali < 0:
        raise ValueError('--casuali non puo essere negativo')
    if not 0.0 < args.holdout_fraction < 1.0:
        raise ValueError('--holdout-fraction deve essere tra 0 e 1')
    if args.bootstrap < 0:
        raise ValueError('--bootstrap non puo essere negativo')
    P.split_shots(args.shots, args.batches)


def main():
    parser = argparse.ArgumentParser(description='M11b — readout effettivo dopo routing')
    parser.add_argument('--sottografi', type=int, default=12)
    parser.add_argument('--shots', type=int, default=8192,
                        help='shot totali per strategia e sottografo')
    parser.add_argument('--batches', type=int, default=8)
    parser.add_argument('--holdout-fraction', type=float, default=0.5)
    parser.add_argument('--bootstrap', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--casuali', type=int, default=2)
    parser.add_argument('--output-dir', type=Path, default=Path('.'))
    parser.add_argument('--checkpoint', type=Path, default=None,
                        help='checkpoint riprendibile (default: nella directory di output)')
    args = parser.parse_args()
    _validate_args(args)

    rng = random.Random(args.seed)
    backend = FakeSherbrooke()
    cal = P.leggi_calibrazione(backend)
    adj = P.coupling_non_orientata(cal)
    qc = P.shor_circuit(P.N, P.A, N_COUNT)
    subgraphs = P.campiona_layout(adj, args.sottografi, P.N_QUBITS, rng)
    if len(subgraphs) < args.sottografi:
        raise RuntimeError(f'Richiesti {args.sottografi} sottografi, ottenuti {len(subgraphs)}')

    shot_schedule = P.split_shots(args.shots, args.batches)
    simulator_seeds = P.seed_schedule(args.seed, args.batches, stream=21)
    n_holdout = max(1, round(args.batches * args.holdout_fraction))
    n_train = args.batches - n_holdout
    if n_train < 1:
        raise ValueError('La frazione holdout non lascia batch di train')

    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = (args.checkpoint if args.checkpoint is not None
                       else args.output_dir / CHECKPOINT_NAME)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    signature = _checkpoint_signature(args, backend, cal)
    righe, fallimenti = _load_checkpoint(checkpoint_path, signature, subgraphs)
    rows_by_id = {int(row['subgraph_id']): row for row in righe}
    failed_keys = {(int(item['subgraph_id']), item['strategy']) for item in fallimenti}

    print(f"Backend snapshot: {backend.name} | sottografi: {len(subgraphs)} | "
          f"{args.shots} shot per strategia")
    print('Le etichette initial-layout sono descrittive; il readout analizzato e quello finale.\n')
    print("  sg  strategia             readout eff.   P_holdout   ECR   depth")
    print("  " + "-" * 73)
    if righe or fallimenti:
        completed = sum(len(row.get('strategie', {})) for row in righe) + len(fallimenti)
        print(f"Ripresa da checkpoint: {completed} strategie gia' elaborate.\n")

    for subgraph_id, layout in enumerate(subgraphs):
        coupling = P.coupling_ridotta(layout, cal)
        strategies = strategie_iniziali(layout, cal, args.casuali, rng)
        row = rows_by_id.get(subgraph_id)
        if row is None:
            row = {
                'subgraph_id': subgraph_id,
                'sottografo': [int(q) for q in layout],
                'strategie': {},
            }
            righe.append(row)
            rows_by_id[subgraph_id] = row
        for name, initial_layout in strategies.items():
            if name in row['strategie'] or (subgraph_id, name) in failed_keys:
                continue
            try:
                result = valuta(
                    qc, layout, coupling, cal, initial_layout,
                    shot_schedule, simulator_seeds, n_train, args.seed,
                )
            except Exception as exc:
                failure = {
                    'subgraph_id': subgraph_id,
                    'strategy': name,
                    'error_type': type(exc).__name__,
                    'message': str(exc),
                }
                fallimenti.append(failure)
                failed_keys.add((subgraph_id, name))
                print(f"  {subgraph_id:<3} {name:<21} errore: {type(exc).__name__}: {exc}")
                _save_checkpoint(checkpoint_path, signature, righe, fallimenti)
                continue
            result['initial_layout'] = (None if initial_layout is None
                                        else [int(q) for q in initial_layout])
            row['strategie'][name] = result
            print(f"  {subgraph_id:<3} {name:<21} {result['readout_misurati']:.5f}       "
                  f"{result['holdout']['P_success']:.4f}      "
                  f"{result['n_ecr']:<5} {result['depth']}", flush=True)
            _save_checkpoint(checkpoint_path, signature, righe, fallimenti)
            gc.collect()
        print()

    analysis_seed = int(args.seed)
    analysis = AR.analizza_righe(
        righe,
        seed=analysis_seed,
        n_bootstrap=args.bootstrap,
        outcome_partition='holdout',
    )
    AR._print_summary(analysis)

    timestamp = datetime.now().astimezone()
    out = {
        'schema_version': '2.0',
        'milestone': 'M11b_ruoli',
        'timestamp': timestamp.isoformat(),
        'seed': args.seed,
        'backend': {
            'name': backend.name,
            'class': type(backend).__name__,
            'num_qubits': int(backend.num_qubits),
            'calibration_sha256': P.calibration_hash(cal),
        },
        'software_versions': P.package_versions(),
        'manifest': P.experiment_manifest(P.N, P.A, P.N_COUNT),
        'noise_model': {
            'revision': P.NOISE_MODEL_REVISION,
            'description': ('target.error converted from average gate infidelity to a '
                            'depolarizing channel; symmetric readout; no separate T1/T2'),
            'rz_virtual': True,
            'ecr_directional': True,
        },
        'design': {
            'type': 'observational within-subgraph',
            'initial_layout_labels_are_not_treatments': True,
            'requested_subgraphs': args.sottografi,
            'valid_subgraphs': sum(bool(row.get('strategie')) for row in righe),
            'analyzable_subgraphs': analysis['n_subgraphs'],
            'random_initial_layouts_per_subgraph': args.casuali,
            'shots_per_strategy': args.shots,
            'batch_shots': shot_schedule,
            'n_train_batches': n_train,
            'n_holdout_batches': args.batches - n_train,
            'common_simulator_seeds': simulator_seeds,
            'common_seed_transpiler': args.seed,
            'basis_gates': P.BASIS,
            'optimization_level': 2,
            'analysis_seed': analysis_seed,
            'bootstrap_resamples': args.bootstrap,
        },
        'analysis': analysis,
        'failures': fallimenti,
        'righe': righe,
    }
    filename = args.output_dir / f"results_M11b_ruoli_v2_{timestamp:%Y%m%d_%H%M%S}.json"
    _write_json_atomic(filename, out)
    _save_checkpoint(
        checkpoint_path, signature, righe, fallimenti,
        status='complete', result=filename,
    )
    print(f'Risultati salvati in: {filename}')


if __name__ == '__main__':
    main()
