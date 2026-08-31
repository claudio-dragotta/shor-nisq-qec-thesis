"""M15b: benchmark della QFT approssimata sulla stima di fase.

PERCHE' NON SU SHOR
M15 ha misurato il compromesso dell'approssimazione su Shor N=21 e ha trovato che non
si vede: quel circuito conta 49.661 porte a due qubit, che a 300 ns l'una fanno ~15 ms
contro un T2 di ~100 us. E' centocinquanta volte la coerenza disponibile, quindi ogni
configurazione finisce sul pavimento uniforme e il confronto non discrimina.

Un benchmark comparativo su Shor misurerebbe percio' il rumore in tre modi diversi.
L'oggetto giusto e' la QFT stessa, nel suo uso canonico: la stima di fase. Una QPE su
n qubit di conteggio con un unitario di fase costa O(n^2) porte a due qubit -- decine,
non decine di migliaia -- quindi sopravvive al rumore realistico e il compromesso e'
osservabile invece che schiacciato.

E' anche la forma in cui il risultato si generalizza: la QPE e' il nucleo condiviso da
Shor, amplitude estimation e da ogni procedura che estragga informazione spettrale.

IL CIRCUITO
Con U = diag(1, e^{2 pi i phi}) e il bersaglio preparato in |1>, l'operazione controllata
U^(2^j) e' una singola rotazione di fase controllata di angolo 2 pi phi 2^j. La parte di
"esponenziazione" costa quindi n porte, e il grosso resta nella QFT inversa: esattamente
la struttura che si vuole studiare, senza l'aritmetica modulare intorno.

IL CONTRASTO CHE SPIEGA M15
Si misurano DUE famiglie di fase:

  esatta            phi = j / 2^n, rappresentabile esattamente in n bit. Le rotazioni
                    fini non trasportano informazione e troncarle costa poco: e' la
                    condizione di N=15, dove r=4 dava fasi 0, 1/4, 1/2, 3/4 e
                    l'approssimazione risultava gratis.
  non rappresentabile  phi = 1/3, 1/6. Le rotazioni fini servono davvero: e' la
                    condizione di N=21, dove r=6 da' fasi j/6.

La differenza fra le due famiglie e' il risultato: dice che il vantaggio
dell'approssimazione non e' una proprieta' del metodo ma della fase da stimare.

METRICA, DICHIARATA PRIMA
Successo = la misura restituisce la MIGLIORE stima a n bit della fase, cioe'
round(phi * 2^n) mod 2^n. E' definita a priori e vale per entrambe le famiglie; per la
fase esatta coincide con il valore esatto.

CRITERIO PREREGISTRATO
Selezione sui batch di train, riporto sui batch di holdout disgiunti, come in M15.
Contrasto primario per ogni configurazione: grado k contro QFT piena, differenza con
IC di Newcombe al 95%.
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime
from fractions import Fraction
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, '..', 'M11_layout'))
sys.path.insert(0, _HERE)

import pilota_layout as P                                    # noqa: E402
from qft_approssimata import (                               # noqa: E402
    inverse_qft_approx,
    newcombe_diff_ci,
    scala_calibrazione,
)

MILESTONE = 'M15b_benchmark_qpe'
REVISION = 'm15b-approximate-qft-phase-estimation-v1'
BASIS = ['sx', 'rz', 'x', 'ecr']

# Fasi bersaglio. Le esatte si generano da n; le non rappresentabili sono fisse.
FASI_NON_RAPPRESENTABILI = {'1/3': Fraction(1, 3), '1/6': Fraction(1, 6)}


def circuito_qpe(n_count, phi, k):
    """QPE su una fase nota, con QFT inversa troncata al grado ``k``.

    Il bersaglio e' preparato in |1>, autostato di U = diag(1, e^{2 pi i phi}).
    L'operazione controllata U^(2^j) collassa in una singola ``cp`` di angolo
    2 pi phi 2^j: l'esponenziazione costa n porte e il resto e' la QFT inversa.
    """
    qc = QuantumCircuit(n_count + 1, n_count)
    bersaglio = n_count
    qc.x(bersaglio)
    for q in range(n_count):
        qc.h(q)
    for j in range(n_count):
        angolo = 2.0 * math.pi * float(phi) * (2 ** j)
        qc.cp(angolo, j, bersaglio)
    qc.barrier()
    qc.append(inverse_qft_approx(n_count, k, elimina_swap=False), range(n_count))
    qc.measure(range(n_count), range(n_count))
    return qc


def stima_migliore(phi, n_count):
    """Migliore stima a n bit della fase: round(phi * 2^n) mod 2^n."""
    return int(round(float(phi) * (2 ** n_count))) % (2 ** n_count)


def conta_successi(counts, phi, n_count):
    atteso = stima_migliore(phi, n_count)
    successi = sum(n for b, n in counts.items()
                   if int(b.replace(' ', ''), 2) == atteso)
    return int(successi), int(sum(counts.values()))


def esegui_batch(tqc, noise_model, shot_schedule, seeds, n_train, phi, n_count):
    sim = AerSimulator(noise_model=noise_model, method='statevector')
    righe = []
    for i, (shots, seed) in enumerate(zip(shot_schedule, seeds)):
        counts = sim.run(tqc, shots=int(shots),
                         seed_simulator=int(seed)).result().get_counts()
        s, t = conta_successi(counts, phi, n_count)
        righe.append({'batch': i,
                      'partition': 'train' if i < n_train else 'holdout',
                      'seed_simulator': int(seed), 'shots': t,
                      'successes': s, 'P_success': s / t})
    return righe


def riassumi(righe, partition=None):
    sel = [r for r in righe if partition is None or r['partition'] == partition]
    s = sum(r['successes'] for r in sel)
    n = sum(r['shots'] for r in sel)
    p = s / n
    return {'P_success': float(p), 'successes': int(s), 'shots': int(n),
            'P_success_se': float((p * (1 - p) / n) ** 0.5), 'n_batches': len(sel)}


def probabilita_ideale(n_count, phi, k):
    """P di ottenere la migliore stima nel circuito senza rumore."""
    sim = AerSimulator()
    qc = circuito_qpe(n_count, phi, k)
    counts = sim.run(transpile(qc, sim, optimization_level=0),
                     shots=20000, seed_simulator=7).result().get_counts()
    s, t = conta_successi(counts, phi, n_count)
    return s / t


def _validate(args):
    if args.batches < 2:
        raise ValueError('Servono almeno due batch per separare train e holdout')
    if not 0.0 < args.holdout_fraction < 1.0:
        raise ValueError('holdout-fraction deve stare in (0,1)')
    if not 0.0 < args.fattore_rumore <= 1.0:
        raise ValueError('fattore-rumore deve stare in (0,1]')


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--n-count', type=int, nargs='+', default=[6, 8, 10])
    ap.add_argument('--shots', type=int, default=4096)
    ap.add_argument('--batches', type=int, default=8)
    ap.add_argument('--holdout-fraction', type=float, default=0.5)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--fattore-rumore', type=float, default=1.0)
    ap.add_argument('--candidati-layout', type=int, default=30)
    ap.add_argument('--output-dir', default='artifacts/benchmark')
    args = ap.parse_args()
    _validate(args)

    backend = FakeSherbrooke()
    cal = P.leggi_calibrazione(backend)
    cal_hash = P.calibration_hash(cal)
    adj = P.coupling_non_orientata(cal)
    cal_rumore = scala_calibrazione(cal, args.fattore_rumore)

    print(f'M15b -- benchmark QPE, registri {args.n_count}, '
          f'fattore rumore {args.fattore_rumore}')
    print(f'metrica: la misura restituisce round(phi*2^n) mod 2^n\n')

    shot_schedule = P.split_shots(args.shots, args.batches)
    seeds = P.seed_schedule(args.seed, args.batches, stream=21)
    n_holdout = max(1, round(args.batches * args.holdout_fraction))
    n_train = args.batches - n_holdout

    punti = []
    for n_count in args.n_count:
        n_qubit = n_count + 1
        rng = np.random.default_rng(args.seed)
        layout = None
        for cand in P.campiona_layout(adj, args.candidati_layout, n_qubit, rng):
            try:
                # Validita' sempre sulla calibrazione REALE, come in M15: altrimenti
                # abbassando il rumore il layout cambierebbe e i livelli non sarebbero
                # confrontabili.
                P.noise_model_layout(cand, cal)
            except ValueError:
                continue
            layout = cand
            break
        if layout is None:
            raise RuntimeError(f'Nessun sottografo valido da {n_qubit} qubit')
        coupling = P.coupling_ridotta(layout, cal)
        nm = P.noise_model_layout(layout, cal_rumore)

        fasi = dict(FASI_NON_RAPPRESENTABILI)
        # Fase esatta: si sceglie j dispari a meta' registro, per non cadere su 0.
        j = (2 ** n_count) // 3 | 1
        fasi[f'{j}/2^{n_count}'] = Fraction(j, 2 ** n_count)

        print(f'--- n_count={n_count}  ({n_qubit} qubit, layout '
              f'{[int(q) for q in layout[:4]]}...)')
        print('  fase          rappr.  k   ecr  P_ideale  P_train  P_holdout')
        for nome, phi in fasi.items():
            rappresentabile = (Fraction(phi).limit_denominator(2 ** n_count)
                               == Fraction(round(float(phi) * 2 ** n_count),
                                           2 ** n_count))
            for k in range(1, n_count):
                qc = circuito_qpe(n_count, phi, k)
                tqc = transpile(qc, basis_gates=BASIS, coupling_map=coupling,
                                optimization_level=3, seed_transpiler=args.seed)
                P.assert_ecr_calibrati(tqc, layout, cal)
                righe = esegui_batch(tqc, nm, shot_schedule, seeds,
                                     n_train, phi, n_count)
                ideale = probabilita_ideale(n_count, phi, k)
                pt = {'n_count': n_count, 'fase': nome, 'phi': float(phi),
                      'rappresentabile': bool(rappresentabile), 'k': k,
                      'k_pieno': n_count - 1,
                      'n_ecr': int(tqc.count_ops().get('ecr', 0)),
                      'depth': int(tqc.depth()),
                      'P_ideale': float(ideale),
                      'layout': [int(q) for q in layout],
                      'train': riassumi(righe, 'train'),
                      'holdout': riassumi(righe, 'holdout'),
                      'batches': righe}
                punti.append(pt)
                print(f"  {nome:<12} {str(rappresentabile):<6} {k:<3} "
                      f"{pt['n_ecr']:5d} {ideale:8.4f} "
                      f"{pt['train']['P_success']:8.4f} "
                      f"{pt['holdout']['P_success']:9.4f}")
        print()

    # Contrasto primario: per ogni (n, fase) il k scelto sul train contro la QFT piena.
    analisi = {'preregistered_rule':
               'select k on train partition, report on disjoint holdout',
               'metric': 'measured value equals round(phi*2^n) mod 2^n',
               'contrasts': []}
    for n_count in args.n_count:
        for nome in {p['fase'] for p in punti if p['n_count'] == n_count}:
            g = [p for p in punti if p['n_count'] == n_count and p['fase'] == nome]
            pieno = next(p for p in g if p['k'] == p['k_pieno'])
            scelto = max(g, key=lambda p: p['train']['P_success'])
            d, lo, hi = newcombe_diff_ci(
                scelto['holdout']['successes'], scelto['holdout']['shots'],
                pieno['holdout']['successes'], pieno['holdout']['shots'])
            analisi['contrasts'].append({
                'n_count': n_count, 'fase': nome,
                'rappresentabile': pieno['rappresentabile'],
                'k_scelto': scelto['k'], 'k_pieno': pieno['k_pieno'],
                'holdout_scelto': scelto['holdout']['P_success'],
                'holdout_pieno': pieno['holdout']['P_success'],
                'difference': d, 'ci_low': lo, 'ci_high': hi,
                'ecr_risparmiate': pieno['n_ecr'] - scelto['n_ecr'],
                'conclusione': ('approssimazione_migliore' if lo > 0 else
                                'approssimazione_peggiore' if hi < 0 else
                                'non_discriminante')})

    out = {'schema_version': '2.0', 'milestone': MILESTONE, 'revision': REVISION,
           'timestamp': datetime.now().astimezone().isoformat(), 'seed': args.seed,
           'config': {'n_count': args.n_count, 'shots': args.shots,
                      'batches': args.batches,
                      'holdout_fraction': args.holdout_fraction,
                      'fattore_rumore': args.fattore_rumore},
           'backend': {'name': backend.name, 'num_qubits': int(backend.num_qubits),
                       'calibration_sha256': cal_hash},
           'software_versions': P.package_versions(),
           'noise_model': {'revision': P.NOISE_MODEL_REVISION,
                           'noise_scaling_factor': args.fattore_rumore},
           'design': {'n_train_batches': n_train, 'n_holdout_batches': n_holdout,
                      'shot_schedule': shot_schedule, 'seed_schedule': seeds},
           'analysis': analisi, 'points': punti}

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = outdir / f'results_M15b_qpe_v1_{stamp}.json'
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')

    print('=== contrasti primari (k scelto sul train, riportato su holdout) ===')
    print('  n   fase          rappr.  k    holdout   piena     diff      esito')
    for c in analisi['contrasts']:
        print(f"  {c['n_count']:<3} {c['fase']:<13} {str(c['rappresentabile']):<6} "
              f"{c['k_scelto']:<4} {c['holdout_scelto']:.4f}   "
              f"{c['holdout_pieno']:.4f}  {c['difference']:+.4f}   "
              f"{c['conclusione']}")
    print(f'\nScritto {path}')


if __name__ == '__main__':
    main()
