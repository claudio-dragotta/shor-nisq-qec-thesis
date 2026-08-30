"""M15: la QFT approssimata aumenta la resa in fattori su una topologia reale?

DOMANDA
Approssimare la trasformata di Fourier -- scartare le rotazioni controllate sotto una
soglia di angolo -- toglie porte e quindi rumore, ma peggiora il circuito ideale. Sotto
rumore i due effetti competono e l'ottimo non e' necessariamente la QFT piena. Questo
esperimento misura dove sta l'ottimo sulla RESA IN FATTORI, non sulla fedelta'.

E' la distinzione che M11 aveva lasciato aperta: il punteggio di fedelta' e' un cattivo
predittore del successo (Spearman -0,184, IC [-0,456; 0,124]), quindi ottimizzare la
fedelta' non e' la stessa cosa che ottimizzare cio' che serve a Shor.

DUE LEVE INDIPENDENTI
  k_qpe    grado della QFT inversa finale del QPE. Si tengono le cp con distanza
           j-m <= k. A n_count=8 le coppie per distanza sono 7,6,5,4,3,2,1 e l'ultima
           rotazione vale pi/128 ~ 0,025 rad, al prezzo di due CX come tutte le altre.
  k_arith  grado delle QFT dentro gli addizionatori di Beauregard (solo N=21). E' qui
           che vive il grosso del costo: la diagnostica di compilazione conta 11.436 cp
           contro 3.406 cx, e quelle cp stanno negli addizionatori, non nel QPE.

Per N=15 il moltiplicatore e' c_amod15, che non contiene QFT: agisce la sola k_qpe, e il
margine atteso e' modesto. N=15 e' quindi un pilota, non il test discriminante.

LIMITE DICHIARATO SU N=15
Con r=4 i picchi cadono su {0,64,128,192}, cioe' fasi 0, 1/4, 1/2, 3/4, rappresentabili
esattamente con DUE bit. L'approssimazione puo' quindi non costare nulla fino a k molto
piccolo, e un esito positivo su N=15 e' debole per costruzione. E' la stessa degenerazione
che ha reso poco discriminante M13. N=21 con r=6 da' fasi j/6 non rappresentabili
esattamente ed e' il test vero.

CRITERIO PREREGISTRATO
La configurazione si sceglie sui batch di TRAIN e si riporta sui batch di HOLDOUT, che
sono disgiunti. Scegliere il massimo su tutte le stime e poi riportarlo sulle stesse
stime e' winner's curse -- la stessa obiezione che M11 si era posta su 60 layout.

Esito primario: P_success su holdout della configurazione selezionata sul train, contro
P_success su holdout della QFT piena, sugli stessi batch e con gli stessi semi.

NON MODIFICA IL CIRCUITO CANONICO
shor_core.py e beauregard.py hanno prodotto gli artefatti v2 e il loro SHA e' vincolato.
Questo script non li tocca: riassembla il circuito dai loro mattoni e applica
l'approssimazione localmente. Il controllo di correttezza verifica che a grado pieno il
circuito ricostruito abbia lo SHA canonico.
"""

import argparse
import contextlib
import hashlib
import json
import os
import sys
from datetime import datetime
from math import ceil, log2
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.synthesis import synth_qft_full
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, '..', 'campagne_classiche_M1-M4'))
sys.path.insert(0, os.path.join(_HERE, '..', 'M11_layout'))

import beauregard                                            # noqa: E402
import pilota_layout as P                                    # noqa: E402
from shor_core import (                                      # noqa: E402
    BASIS_GATES,
    TRANSPILE_SEED,
    c_amod15,
    circuit_fingerprint,
    experiment_manifest,
    extract_factors,
)
from beauregard import beauregard_c_amod                     # noqa: E402

MILESTONE = 'M15_qft_approssimata'
REVISION = 'm15-approximate-qft-topology-aware-v1'
BASIS = ['sx', 'rz', 'x', 'ecr']

# Istanze ammesse. Il perimetro e' N=15 e N=21 per indicazione del relatore del 28/08/2026.
ISTANZE = {
    15: {'a': 7, 'n_count': 8, 'n_work': 4, 'r': 4, 'ha_qft_aritmetica': False},
    21: {'a': 2, 'n_count': 8, 'n_work': None, 'r': 6, 'ha_qft_aritmetica': True},
}


# --------------------------------------------------------------------------------------
# Costruzione del circuito approssimato
# --------------------------------------------------------------------------------------

def inverse_qft_approx(n_qubits, k, elimina_swap):
    """QFT inversa con troncamento delle rotazioni e SWAP opzionali.

    ``k`` e' la distanza massima ``j-m`` per cui la cp viene mantenuta. ``k >= n-1``
    riproduce la QFT piena.

    ``elimina_swap=True`` toglie i SWAP di inversione dei bit. ATTENZIONE: nella forma
    canonica i SWAP stanno PRIMA della cascata, non dopo, quindi non basta rinominare i
    bit classici alla misura -- quella scorciatoia produce un circuito diverso, con
    P_success ideale 0,4542 invece di 0,7505 e picchi in 0/255/128 invece di
    0/64/128/192. Verificato il 30/08/2026 e corretto.

    La forma giusta e' per coniugazione. Detta ``R`` l'inversione dei bit e ``C`` la
    cascata, la QFT inversa e' ``C R``; posto ``C' = R C R`` vale ``C R = R C'``, quindi
    si applica la cascata sugli indici invertiti e la ``R`` finale si assorbe nella
    mappatura classica. Il chiamante deve quindi misurare con ordine invertito.
    """
    if k < 1:
        raise ValueError('k deve essere almeno 1: k=0 elimina ogni rotazione')
    qc = QuantumCircuit(n_qubits, name=f'QFT†~{k}')
    if elimina_swap:
        # Cascata coniugata: indice i -> n-1-i.
        for j in range(n_qubits):
            for m in range(j):
                if j - m <= k:
                    qc.cp(-np.pi / float(2 ** (j - m)),
                          n_qubits - 1 - m, n_qubits - 1 - j)
            qc.h(n_qubits - 1 - j)
    else:
        for qubit in range(n_qubits // 2):
            qc.swap(qubit, n_qubits - qubit - 1)
        for j in range(n_qubits):
            for m in range(j):
                if j - m <= k:
                    qc.cp(-np.pi / float(2 ** (j - m)), m, j)
            qc.h(j)
    return qc


@contextlib.contextmanager
def qft_aritmetica(k_arith, n_b):
    """Applica temporaneamente il grado ``k_arith`` alle QFT interne di Beauregard.

    ``beauregard._qft`` e' chiamata sette volte dentro gli addizionatori. Si sostituisce
    per la durata del blocco e si ripristina sempre, anche in caso di eccezione: il
    modulo canonico deve restare quello che ha prodotto gli artefatti v2.

    ``approximation_degree`` di ``synth_qft_full`` conta le rotazioni SCARTATE, quindi il
    grado di troncamento ``k`` corrisponde a ``approximation_degree = n_b - k``.
    """
    originale = beauregard._qft
    if k_arith is None:
        yield 0
        return
    scartate = max(0, int(n_b) - int(k_arith))

    def _qft_approssimata(n, inverse=False):
        return synth_qft_full(n, do_swaps=False, inverse=inverse,
                              approximation_degree=min(scartate, max(0, n - 1)))

    beauregard._qft = _qft_approssimata
    try:
        yield scartate
    finally:
        beauregard._qft = originale


def shor_circuit_approx(N, a, n_count, k_qpe, k_arith, elimina_swap):
    """Riassembla il circuito di Shor con QFT approssimata.

    Riproduce l'assemblaggio di ``shor_core.shor_circuit`` usandone i mattoni, senza
    modificarlo. A grado pieno e SWAP presenti deve dare lo stesso circuito canonico.
    """
    if N == 15:
        n_work = 4
        qc = QuantumCircuit(n_count + n_work, n_count)
        for q in range(n_count):
            qc.h(q)
        qc.x(n_count + 3)
        for j in range(n_count):
            if 2 ** j % 4 != 0:
                qc.append(c_amod15(a, 2 ** j),
                          [j] + list(range(n_count, n_count + n_work)))
    elif N == 21:
        n = ceil(log2(N + 1))
        n_b = n + 1
        n_total = n_count + n + n_b + 1
        qc = QuantumCircuit(n_total, n_count)
        for q in range(n_count):
            qc.h(q)
        qc.x(n_count + n - 1)
        with qft_aritmetica(k_arith, n_b):
            for j in range(n_count):
                power = 2 ** j
                if pow(a, power, N) != 1:
                    gate = beauregard_c_amod(a, N, power)
                    x_qubits = list(range(n_count, n_count + n))
                    b_qubits = list(range(n_count + n, n_count + n + n_b))
                    anc_qubit = [n_count + n + n_b]
                    qc.append(gate, [j] + x_qubits + b_qubits + anc_qubit)
    else:
        raise ValueError(f'N={N} fuori perimetro: ammessi {sorted(ISTANZE)}')

    qc.barrier()
    qc.append(inverse_qft_approx(n_count, k_qpe, elimina_swap), range(n_count))
    if elimina_swap:
        # I SWAP invertivano l'ordine dei bit: si assorbono nella mappatura classica.
        qc.measure(range(n_count), list(reversed(range(n_count))))
    else:
        qc.measure(range(n_count), range(n_count))
    return qc


def verifica_circuito_canonico(N, a, n_count):
    """A grado pieno il circuito ricostruito deve avere lo SHA canonico."""
    k_pieno = n_count - 1
    ricostruito = shor_circuit_approx(N, a, n_count, k_pieno, None, elimina_swap=False)
    compilato = transpile(ricostruito, basis_gates=list(BASIS_GATES),
                          optimization_level=2, seed_transpiler=TRANSPILE_SEED)
    atteso = experiment_manifest(N, a, n_count)['circuit_sha256']
    ottenuto = circuit_fingerprint(compilato)
    if ottenuto != atteso:
        raise RuntimeError(
            'Il circuito ricostruito a grado pieno NON coincide con il canonico.\n'
            f'  atteso  {atteso}\n  ottenuto {ottenuto}\n'
            'Interrotto: senza questa identita\' i confronti non sono interpretabili.')
    return atteso


# --------------------------------------------------------------------------------------
# Misura
# --------------------------------------------------------------------------------------

def conta_successi(counts, N, a, n_count):
    """Successi = esiti da cui il post-processing estrae un fattore. Non e' fedelta'."""
    successi, totale = 0, sum(counts.values())
    for bit, n in counts.items():
        value = int(bit.replace(' ', ''), 2)
        if extract_factors(value, n_count, N, a)[0] is not None:
            successi += n
    return int(successi), int(totale)


def esegui_batch(tqc, noise_model, shot_schedule, seeds, n_train, N, a, n_count):
    if len(shot_schedule) != len(seeds):
        raise ValueError('shot_schedule e seeds devono avere la stessa lunghezza')
    if not 0 < n_train < len(seeds):
        raise ValueError('n_train deve lasciare almeno un batch di holdout')
    sim = AerSimulator(noise_model=noise_model, method='statevector')
    righe = []
    for index, (shots, seed) in enumerate(zip(shot_schedule, seeds)):
        counts = sim.run(tqc, shots=int(shots),
                         seed_simulator=int(seed)).result().get_counts()
        successi, totale = conta_successi(counts, N, a, n_count)
        righe.append({
            'batch': index,
            'partition': 'train' if index < n_train else 'holdout',
            'seed_simulator': int(seed),
            'shots': totale,
            'successes': successi,
            'P_success': successi / totale,
        })
    return righe


def riassumi(righe, partition=None):
    scelte = [r for r in righe if partition is None or r['partition'] == partition]
    if not scelte:
        raise ValueError(f'Nessun batch per partition={partition!r}')
    successi = sum(r['successes'] for r in scelte)
    shots = sum(r['shots'] for r in scelte)
    p = successi / shots
    return {'P_success': float(p),
            'P_success_se': float((p * (1.0 - p) / shots) ** 0.5),
            'successes': int(successi), 'shots': int(shots), 'n_batches': len(scelte)}


def newcombe_diff_ci(s1, n1, s2, n2, z=1.959963985):
    """IC di Newcombe per la differenza di due proporzioni indipendenti.

    Stessa convenzione usata da M13 per il contrasto primario.
    """
    def wilson(s, n):
        if n == 0:
            return 0.0, 0.0
        p = s / n
        d = 1.0 + z * z / n
        centro = (p + z * z / (2 * n)) / d
        mezzo = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
        return max(0.0, centro - mezzo), min(1.0, centro + mezzo)

    l1, u1 = wilson(s1, n1)
    l2, u2 = wilson(s2, n2)
    diff = s1 / n1 - s2 / n2
    basso = diff - ((s1 / n1 - l1) ** 2 + (u2 - s2 / n2) ** 2) ** 0.5
    alto = diff + ((u1 - s1 / n1) ** 2 + (s2 / n2 - l2) ** 2) ** 0.5
    return float(diff), float(max(-1.0, basso)), float(min(1.0, alto))


# --------------------------------------------------------------------------------------
# Griglia e main
# --------------------------------------------------------------------------------------

def griglia(n_count, ha_qft_aritmetica, n_b, k_arith_max):
    """Configurazioni da valutare. La QFT piena e' sempre inclusa come riferimento."""
    k_pieno = n_count - 1
    config = []
    for elimina_swap in (False, True):
        for k_qpe in range(1, k_pieno + 1):
            if ha_qft_aritmetica:
                for k_arith in range(1, k_arith_max + 1):
                    config.append({'k_qpe': k_qpe, 'k_arith': k_arith,
                                   'elimina_swap': elimina_swap})
                config.append({'k_qpe': k_qpe, 'k_arith': n_b,
                               'elimina_swap': elimina_swap})
            else:
                config.append({'k_qpe': k_qpe, 'k_arith': None,
                               'elimina_swap': elimina_swap})
    # Deduplica conservando l'ordine.
    viste, uniche = set(), []
    for c in config:
        chiave = (c['k_qpe'], c['k_arith'], c['elimina_swap'])
        if chiave not in viste:
            viste.add(chiave)
            uniche.append(c)
    return uniche


def e_riferimento(config, n_count, n_b, ha_qft_aritmetica):
    """La QFT piena con SWAP: e' il termine di paragone dell'esito primario."""
    if config['elimina_swap'] or config['k_qpe'] != n_count - 1:
        return False
    return config['k_arith'] == (n_b if ha_qft_aritmetica else None)


def _validate(args):
    if args.N not in ISTANZE:
        raise ValueError(f'N={args.N} fuori perimetro: ammessi {sorted(ISTANZE)}')
    if args.batches < 2:
        raise ValueError('Servono almeno due batch per separare train e holdout')
    if not 0.0 < args.holdout_fraction < 1.0:
        raise ValueError('holdout-fraction deve stare in (0,1)')


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--N', type=int, default=15, choices=sorted(ISTANZE))
    ap.add_argument('--shots', type=int, default=8192)
    ap.add_argument('--batches', type=int, default=8)
    ap.add_argument('--holdout-fraction', type=float, default=0.5)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--k-arith-max', type=int, default=4,
                    help='grado massimo esplorato per le QFT aritmetiche (solo N=21)')
    ap.add_argument('--candidati-layout', type=int, default=20,
                    help='sottografi da campionare per trovarne uno con AGI nel dominio')
    ap.add_argument('--solo-struttura', action='store_true',
                    help='misura solo conteggi porte e profondita, senza simulare')
    ap.add_argument('--output-dir', default='artifacts')
    args = ap.parse_args()
    _validate(args)

    spec = ISTANZE[args.N]
    a, n_count = spec['a'], spec['n_count']
    n = ceil(log2(args.N + 1))
    n_b = n + 1 if spec['ha_qft_aritmetica'] else None

    print(f'M15 -- QFT approssimata, N={args.N}, a={a}, n_count={n_count}')
    print('Controllo di correttezza: circuito a grado pieno contro SHA canonico...')
    sha_canonico = verifica_circuito_canonico(args.N, a, n_count)
    print(f'  OK  {sha_canonico[:16]}...\n')

    backend = FakeSherbrooke()
    cal = P.leggi_calibrazione(backend)
    cal_hash = P.calibration_hash(cal)
    adj = P.coupling_non_orientata(cal)

    # Layout fisso: M15 non fa variare il collocamento -- quello e' l'oggetto di M11.
    n_qubits_circuito = shor_circuit_approx(args.N, a, n_count,
                                            n_count - 1, n_b, False).num_qubits
    # Come in M11, una parte dei sottografi porta un gate con AGI pari a 1, fuori dal
    # dominio della conversione depolarizzante: li' erano 20 su 60. Si campiona finche'
    # non se ne trova uno valido, e si registra quanti sono stati scartati.
    rng = np.random.default_rng(args.seed)
    candidati = P.campiona_layout(adj, args.candidati_layout, n_qubits_circuito, rng)
    if not candidati:
        raise RuntimeError(f'Nessun sottografo connesso da {n_qubits_circuito} qubit')
    layout, coupling, noise_model, scartati = None, None, None, []
    for candidato in candidati:
        try:
            nm = None if args.solo_struttura else P.noise_model_layout(candidato, cal)
        except ValueError as exc:
            scartati.append({'layout': [int(q) for q in candidato], 'motivo': str(exc)})
            continue
        layout, coupling, noise_model = candidato, P.coupling_ridotta(candidato, cal), nm
        break
    if layout is None:
        raise RuntimeError(
            f'Nessuno dei {len(candidati)} sottografi campionati ha un modello di rumore '
            'valido: tutti contengono un gate con AGI fuori dominio. '
            'Aumentare --candidati-layout.')
    if scartati:
        print(f'  {len(scartati)} sottografi scartati per AGI fuori dominio '
              'prima di trovarne uno valido')
    print(f'Layout fisso: {[int(q) for q in layout[:6]]}... '
          f'({len(layout)} qubit)\n')

    shot_schedule = P.split_shots(args.shots, args.batches)
    seeds = P.seed_schedule(args.seed, args.batches, stream=15)
    n_holdout = max(1, round(args.batches * args.holdout_fraction))
    n_train = args.batches - n_holdout
    if n_train < 1:
        raise ValueError('La frazione holdout non lascia batch di train')

    config = griglia(n_count, spec['ha_qft_aritmetica'], n_b, args.k_arith_max)
    print(f'{len(config)} configurazioni, {args.batches} batch '
          f'({n_train} train / {n_holdout} holdout)\n')
    print('  k_qpe  k_arith  swap  ecr   depth   P_train   P_holdout')
    print('  ' + '-' * 60)

    punti = []
    for c in config:
        # shor_circuit_approx apre da se' il contesto sulle QFT aritmetiche: non va
        # avvolto una seconda volta.
        qc = shor_circuit_approx(args.N, a, n_count, c['k_qpe'],
                                 c['k_arith'], c['elimina_swap'])
        tqc = transpile(qc, basis_gates=BASIS, coupling_map=coupling,
                        optimization_level=3, seed_transpiler=args.seed)
        P.assert_ecr_calibrati(tqc, layout, cal)
        ops = {str(k): int(v) for k, v in tqc.count_ops().items()}
        punto = {
            **c,
            'is_riferimento': e_riferimento(c, n_count, n_b,
                                            spec['ha_qft_aritmetica']),
            'depth': int(tqc.depth()),
            'size': int(tqc.size()),
            'n_ecr': int(ops.get('ecr', 0)),
            'operations': ops,
            'punteggio_fedelta': float(P.punteggio_fedelta(tqc, layout, cal)),
        }
        if not args.solo_struttura:
            righe = esegui_batch(tqc, noise_model, shot_schedule, seeds,
                                 n_train, args.N, a, n_count)
            punto['batches'] = righe
            punto['train'] = riassumi(righe, 'train')
            punto['holdout'] = riassumi(righe, 'holdout')
            punto['P_success'] = riassumi(righe)['P_success']
        punti.append(punto)
        ka = '-' if c['k_arith'] is None else c['k_arith']
        sw = 'no' if c['elimina_swap'] else 'si'
        if args.solo_struttura:
            print(f"  {c['k_qpe']:5d}  {str(ka):>7}  {sw:>4} {punto['n_ecr']:5d} "
                  f"{punto['depth']:7d}         -           -")
        else:
            print(f"  {c['k_qpe']:5d}  {str(ka):>7}  {sw:>4} {punto['n_ecr']:5d} "
                  f"{punto['depth']:7d}   {punto['train']['P_success']:.4f}"
                  f"    {punto['holdout']['P_success']:.4f}")

    analisi = {'preregistered_rule':
               'select on train partition, report on disjoint holdout partition'}
    if not args.solo_struttura:
        rif = next((p for p in punti if p['is_riferimento']), None)
        scelto = max(punti, key=lambda p: p['train']['P_success'])
        analisi['selected_on_train'] = {k: scelto[k] for k in
                                        ('k_qpe', 'k_arith', 'elimina_swap')}
        analisi['selected_holdout'] = scelto['holdout']
        if rif is not None:
            analisi['reference_full_qft_holdout'] = rif['holdout']
            diff, lo, hi = newcombe_diff_ci(
                scelto['holdout']['successes'], scelto['holdout']['shots'],
                rif['holdout']['successes'], rif['holdout']['shots'])
            analisi['primary_contrast'] = {
                'description': 'holdout P_success: selected minus full QFT',
                'difference': diff, 'ci_low': lo, 'ci_high': hi,
                'method': 'Newcombe hybrid score, 95%',
                'conclusion': ('approximation_not_worse' if lo > -0.01 else
                               'approximation_worse'),
            }
            analisi['ecr_reduction'] = {
                'reference': rif['n_ecr'], 'selected': scelto['n_ecr'],
                'delta': rif['n_ecr'] - scelto['n_ecr'],
            }
        analisi['caveat_N15_degenerate'] = (args.N == 15)

    out = {
        'schema_version': '2.0',
        'milestone': MILESTONE,
        'revision': REVISION,
        'timestamp': datetime.now().astimezone().isoformat(),
        'seed': args.seed,
        'config': {'N': args.N, 'a': a, 'n_count': n_count,
                   'shots': args.shots, 'batches': args.batches,
                   'holdout_fraction': args.holdout_fraction,
                   'k_arith_max': args.k_arith_max,
                   'solo_struttura': bool(args.solo_struttura)},
        'backend': {'name': backend.name, 'class': type(backend).__name__,
                    'num_qubits': int(backend.num_qubits),
                    'calibration_sha256': cal_hash},
        'software_versions': P.package_versions(),
        'manifest': experiment_manifest(args.N, a, n_count),
        'canonical_circuit_sha256': sha_canonico,
        'noise_model': {'revision': P.NOISE_MODEL_REVISION,
                        'description': 'per-qubit depolarizing from calibration AGI, '
                                       'symmetric readout, rz virtual'},
        'design': {'layout': [int(q) for q in layout],
                   'layout_scartati_agi_fuori_dominio': scartati,
                   'n_train_batches': n_train, 'n_holdout_batches': n_holdout,
                   'shot_schedule': shot_schedule,
                   'seed_schedule': seeds},
        'analysis': analisi,
        'points': punti,
    }

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = outdir / f'results_M15_qft_N{args.N}_v1_{stamp}.json'
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'\nScritto {path}')
    if not args.solo_struttura and 'primary_contrast' in analisi:
        pc = analisi['primary_contrast']
        print(f"Esito primario: differenza {pc['difference']:+.4f} "
              f"IC 95% [{pc['ci_low']:+.4f}; {pc['ci_high']:+.4f}] -> {pc['conclusion']}")
        er = analisi['ecr_reduction']
        print(f"Porte a due qubit: {er['reference']} -> {er['selected']} "
              f"({er['delta']:+d})")
    if args.N == 15:
        print('\nAVVERTENZA: con r=4 le fasi sono 0, 1/4, 1/2, 3/4, esatte in due bit.')
        print('Un esito positivo su N=15 e\' debole per costruzione: il test '
              'discriminante e\' N=21.')


if __name__ == '__main__':
    main()
