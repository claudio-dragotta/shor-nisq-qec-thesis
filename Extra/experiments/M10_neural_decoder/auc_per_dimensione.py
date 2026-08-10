"""
auc_per_dimensione.py — Milestone M10, esperimento E12: la rete e' cieca o solo indecisa?

E9 riporta che a 336 detector il residuo "si astiene". Ma astenersi e' l'esito di una
SELEZIONE: fra le soglie candidate c'e' 1.01 ("non ribaltare mai"), e in validazione
nessuna soglia di ribaltamento l'ha battuta. Da questo non segue che la rete non veda
nulla --- segue solo che non conviene agire su cio' che vede.

La distinzione ha conseguenze pratiche opposte, e la tesi ne raccomanda una:

  AUC ~ 0.5   la rete non discrimina affatto: il vincolo e' rappresentativo, e il rimedio
              e' un'architettura che sfrutti la simmetria del reticolo (convoluzionale o
              a grafo). E' la raccomandazione attualmente scritta.

  AUC alta    la rete ordina bene i casi ma la regola di decisione non riesce a
              trasformare quell'ordinamento in un guadagno --- tipicamente perche' i
              fallimenti che riconosce sono meno dei falsi positivi che introdurrebbe.
              Il rimedio sarebbe allora la regola di decisione, non l'architettura, e la
              raccomandazione andrebbe corretta.

Si misura l'AUC del residuo (bersaglio: "il MWPM ha sbagliato") sul test set, insieme
alla soglia scelta e al guadagno che la soglia MIGLIORE IN ASSOLUTO avrebbe prodotto sul
test --- un valore ottimistico, non utilizzabile in pratica perche' sceglie sui dati di
valutazione, ma che quantifica quanto si perde nella sola calibrazione.

Uso (WSL, quantum-env):
    ~/quantum-env/bin/python auc_per_dimensione.py
"""
import argparse
import json
import time
from datetime import datetime

import numpy as np
from sklearn.metrics import roc_auc_score

from qec_neural_decoder import (
    build_circuit, with_crosstalk, sample, matcher, mwpm_predict, train_nn,
    binom_se, P_PHYS,
)

CELLE = [(3, 3), (5, 5), (7, 3), (5, 14), (7, 7)]   # (distanza, cicli) -> 24..336 detector
PCT_LIST = [0.005, 0.02]
SOGLIE = list(np.round(np.arange(0.02, 0.99, 0.02), 2)) + [1.01]


def run_punto(d, rounds, p, p_ct, shots, seed):
    t0 = time.time()
    circ_nom = build_circuit(d, p, rounds=rounds)
    det, y = sample(with_crosstalk(circ_nom, p_ct), shots, seed)
    pred = mwpm_predict(matcher(circ_nom), det)

    n_tr, n_va = int(shots * 0.60), int(shots * 0.15)
    tr, va, te = slice(0, n_tr), slice(n_tr, n_tr + n_va), slice(n_tr + n_va, None)
    y_te, n_te = y[te], len(y[te])

    X = np.concatenate([det, pred[:, None]], axis=1)
    err = (pred != y)
    nn = train_nn(X[tr], err[tr], seed)

    pe_va = nn.predict_proba(X[va].astype(np.float32))[:, 1]
    pe_te = nn.predict_proba(X[te].astype(np.float32))[:, 1]

    # AUC sul test: quanto la rete ORDINA i fallimenti del matching, indipendentemente
    # da qualunque soglia. E' la quantita' che distingue "cieca" da "indecisa".
    auc = float(roc_auc_score(err[te], pe_te)) if err[te].any() else float('nan')

    pL_mwpm = float((pred[te] != y_te).mean())

    # soglia onesta: scelta in validazione
    punteggi_va = {t: float(((pred[va] ^ (pe_va >= t)) != y[va]).mean()) for t in SOGLIE}
    thr = min(punteggi_va, key=punteggi_va.get)
    pL_onesto = float(((pred[te] ^ (pe_te >= thr)) != y_te).mean())

    # soglia oracolo: la migliore SUL TEST. Non utilizzabile (sceglie sui dati di
    # valutazione), ma misura quanto del divario e' imputabile alla sola calibrazione.
    punteggi_te = {t: float(((pred[te] ^ (pe_te >= t)) != y_te).mean()) for t in SOGLIE}
    thr_or = min(punteggi_te, key=punteggi_te.get)
    pL_oracolo = punteggi_te[thr_or]

    return {
        'd': d, 'rounds': rounds, 'p': p, 'p_crosstalk': p_ct, 'shots': shots,
        'seed': seed, 'n_detectors': int(det.shape[1]), 'n_test': n_te,
        'esempi_positivi_train': int(err[tr].sum()),
        'auc_residuo': auc,
        'pL_mwpm': pL_mwpm, 'pL_mwpm_se': binom_se(pL_mwpm, n_te),
        'soglia_validazione': float(thr), 'pL_soglia_onesta': pL_onesto,
        'guadagno_onesto': pL_mwpm / pL_onesto if pL_onesto else None,
        'soglia_oracolo': float(thr_or), 'pL_soglia_oracolo': pL_oracolo,
        'guadagno_oracolo': pL_mwpm / pL_oracolo if pL_oracolo else None,
        'secs': round(time.time() - t0, 1),
    }


def main():
    ap = argparse.ArgumentParser(description="M10/E12 — AUC del residuo per dimensione")
    ap.add_argument('--shots', type=int, default=800_000)
    args = ap.parse_args()

    t0 = time.time()
    print("=" * 78)
    print("E12 — A 336 DETECTOR LA RETE E' CIECA O SOLO INDECISA?")
    print("    AUC ~ 0.5 -> cieca, serve un'altra architettura")
    print("    AUC alta  -> vede ma non conviene agire: sarebbe la regola di decisione")
    print("=" * 78)

    out = {'milestone': 'M10_auc_per_dimensione', 'timestamp': datetime.now().isoformat(),
           'p_phys': P_PHYS, 'shots_per_config': args.shots, 'points': []}

    for d, rounds in CELLE:
        for pct in PCT_LIST:
            r = run_punto(d, rounds, P_PHYS, pct, args.shots,
                          seed=12_000 + d * 100 + rounds)
            print(f"  det={r['n_detectors']:<4} d={d} cicli={rounds:<2} p_ct={pct:<6g}  "
                  f"AUC={r['auc_residuo']:.4f}  "
                  f"soglia={r['soglia_validazione']:.2f}  "
                  f"onesto={r['guadagno_onesto']:.4f}x  "
                  f"oracolo={r['guadagno_oracolo']:.4f}x   [{r['secs']}s]", flush=True)
            out['points'].append(r)
            with open(f"results_M10_auc_{datetime.now():%Y%m%d}.json", 'w') as f:
                json.dump(out, f, indent=2)

    print(f"\nTempo totale: {(time.time()-t0)/60:.1f} min")


if __name__ == '__main__':
    main()
