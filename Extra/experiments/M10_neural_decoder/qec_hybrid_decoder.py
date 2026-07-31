"""
qec_hybrid_decoder.py — Milestone M10, esperimento E4: decoder IBRIDO MWPM + rete.

Da E2 sappiamo che la rete, come decoder autonomo, batte MWPM a d=3 sotto rumore correlato
ma perde a d=5 (lo spazio delle sindromi cresce piu' in fretta della sua capacita').
Da E3 sappiamo pero' che la rete riconosce gli shot in cui MWPM sbaglia con AUC 0.94.
E4 mette insieme le due cose: invece di SOSTITUIRE il decoder analitico, la rete impara
QUANDO RIBALTARLO.

    predizione finale  =  pred_MWPM  XOR  [ rete dice "MWPM ha sbagliato" ]

E' la forma residuale, e ha tre proprieta' che la rendono preferibile alla sostituzione:
  1. degrada con grazia: alzando la soglia fino a "non ribaltare mai" si ricade esattamente
     su MWPM, quindi l'ibrido non puo' fare sistematicamente peggio del decoder analitico;
  2. la rete impara un compito piu' facile (un residuo raro e strutturato) invece di
     riprodurre da zero il calcolo di parita' che MWPM gia' esegue correttamente;
  3. corrisponde alla richiesta del relatore (2026-07-08): una rete che conferma o nega
     la correzione proposta dal circuito ancillare.

La soglia di ribaltamento e' scelta su un insieme di VALIDAZIONE separato e poi applicata
al test set: sceglierla sul test sarebbe una fuga di informazione.

Uso (WSL, quantum-env):
    ~/quantum-env/bin/python qec_hybrid_decoder.py
    ~/quantum-env/bin/python qec_hybrid_decoder.py --shots 100000 --distances 5
"""
import argparse
import json
import math
import time
from datetime import datetime

import numpy as np

from qec_neural_decoder import (
    build_circuit, with_crosstalk, sample, matcher, mwpm_predict, train_nn,
    binom_se, P_PHYS, PCT_LIST_E2,
)

FRAC_TRAIN, FRAC_VAL = 0.60, 0.15
# la soglia 1.01 significa "non ribaltare mai": garantisce l'ibrido >= MWPM in validazione
THRESHOLDS = list(np.round(np.arange(0.10, 0.96, 0.05), 2)) + [1.01]


def run_hybrid(d, p, shots, seed, p_ct=0.0):
    t0 = time.time()
    circ_nom = build_circuit(d, p)
    circ_real = with_crosstalk(circ_nom, p_ct)
    det, y = sample(circ_real, shots, seed)

    # MWPM con il modello nominale (cio' che l'operatore crede), su tutti gli shot
    pred = mwpm_predict(matcher(circ_nom), det)

    n_tr = int(shots * FRAC_TRAIN)
    n_va = int(shots * FRAC_VAL)
    tr = slice(0, n_tr)
    va = slice(n_tr, n_tr + n_va)
    te = slice(n_tr + n_va, None)
    n_te = len(y[te])

    # --- braccio 1: MWPM da solo ---
    pL_mwpm = float((pred[te] != y[te]).mean())

    # --- braccio 2: rete come decoder autonomo (sostituzione) ---
    nn = train_nn(det[tr], y[tr], seed)
    pL_nn = float(((nn.predict_proba(det[te].astype(np.float32))[:, 1] >= 0.5) != y[te]).mean())

    # --- braccio 3: ibrido residuale (la rete decide quando ribaltare MWPM) ---
    X = np.concatenate([det, pred[:, None]], axis=1)
    err = (pred != y)                      # bersaglio: "MWPM ha sbagliato"
    nnh = train_nn(X[tr], err[tr], seed)

    pe_va = nnh.predict_proba(X[va].astype(np.float32))[:, 1]
    scores = {t: float(((pred[va] ^ (pe_va >= t)) != y[va]).mean()) for t in THRESHOLDS}
    thr = min(scores, key=scores.get)      # soglia scelta SOLO in validazione

    pe_te = nnh.predict_proba(X[te].astype(np.float32))[:, 1]
    flip = pe_te >= thr
    final = pred[te] ^ flip
    pL_hyb = float((final != y[te]).mean())

    # McNemar appaiato: ibrido e MWPM differiscono SOLO sugli shot ribaltati, quindi le
    # coppie discordanti sono esattamente quelle. Test piu' potente della stima binomiale
    # non appaiata, che ignora la correlazione fra i due bracci sugli stessi campioni.
    err_m = (pred[te] != y[te])
    err_h = (final != y[te])
    b = int((err_h & ~err_m).sum())      # l'ibrido rompe cio' che MWPM aveva risolto
    c = int((~err_h & err_m).sum())      # l'ibrido aggiusta cio' che MWPM aveva sbagliato
    if b + c > 0:
        chi2 = (b - c) ** 2 / (b + c)
        pval = math.erfc(math.sqrt(chi2 / 2))
    else:
        chi2, pval = 0.0, 1.0

    return {
        'd': d, 'p': p, 'p_crosstalk': p_ct, 'shots': shots, 'seed': seed,
        'n_detectors': int(det.shape[1]), 'n_train': n_tr, 'n_val': n_va, 'n_test': n_te,
        'base_rate': float(y.mean()),
        'pL_mwpm': pL_mwpm, 'pL_mwpm_se': binom_se(pL_mwpm, n_te),
        'pL_nn': pL_nn, 'pL_nn_se': binom_se(pL_nn, n_te),
        'pL_hybrid': pL_hyb, 'pL_hybrid_se': binom_se(pL_hyb, n_te),
        'threshold': float(thr), 'flip_rate': float(flip.mean()),
        'gain_hybrid_vs_mwpm': (pL_mwpm / pL_hyb) if pL_hyb > 0 else None,
        'mcnemar': {'b_peggiora': b, 'c_migliora': c, 'chi2': float(chi2),
                    'p_value': float(pval)},
        'secs': round(time.time() - t0, 1),
    }


def fmt(r):
    g = r['gain_hybrid_vs_mwpm']
    return (f"  d={r['d']} p_ct={r['p_crosstalk']:<6g}  "
            f"MWPM={r['pL_mwpm']:.5f}  rete={r['pL_nn']:.5f}  "
            f"IBRIDO={r['pL_hybrid']:.5f}  "
            f"(soglia {r['threshold']:.2f}, ribalta {r['flip_rate']*100:.2f}%)  "
            f"|  ibrido/MWPM={g:.2f}x  McNemar p={r['mcnemar']['p_value']:.1e}"
            + f"  [{r['secs']}s]")


def main():
    ap = argparse.ArgumentParser(description="M10/E4 — decoder ibrido MWPM + rete")
    ap.add_argument('--shots', type=int, default=400_000)
    ap.add_argument('--distances', type=int, nargs='+', default=[3, 5])
    args = ap.parse_args()

    t0 = time.time()
    print("=" * 78)
    print("E4 — DECODER IBRIDO: la rete non sostituisce MWPM, impara quando ribaltarlo")
    print(f"    p fisico = {P_PHYS}; soglia scelta in validazione, riportata sul test set")
    print("=" * 78)

    out = {'milestone': 'M10_hybrid_decoder', 'timestamp': datetime.now().isoformat(),
           'p_phys': P_PHYS, 'shots_per_config': args.shots,
           'frac_train': FRAC_TRAIN, 'frac_val': FRAC_VAL, 'points': []}

    for d in args.distances:
        for i, pct in enumerate([0.0] + PCT_LIST_E2):
            r = run_hybrid(d, P_PHYS, args.shots, seed=4000 + d * 100 + i, p_ct=pct)
            print(fmt(r), flush=True)
            out['points'].append(r)

    wins = sum(1 for r in out['points']
               if r['pL_hybrid'] < r['pL_mwpm'] - 2 * (r['pL_hybrid_se'] ** 2
                                                       + r['pL_mwpm_se'] ** 2) ** 0.5)
    out['hybrid_wins_2sigma'] = wins
    print(f"\nFLAG E4: l'ibrido batte MWPM (oltre 2 sigma) in {wins}/{len(out['points'])} "
          f"configurazioni")

    fname = f"results_M10_hybrid_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(fname, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nTempo totale: {(time.time()-t0)/60:.1f} min")
    print(f"Risultati salvati in: {fname}")


if __name__ == '__main__':
    main()
