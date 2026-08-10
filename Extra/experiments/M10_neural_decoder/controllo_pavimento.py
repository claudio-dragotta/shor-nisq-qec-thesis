"""
controllo_pavimento.py — Milestone M10, esperimento E11: il pavimento e' della sindrome
o della rete?

E10 ha rilevato che tre metodi diversi --- il matching col residuo, BP+OSD col residuo e
la rete usata da sola --- atterrano entro l'1-2% sul medesimo errore logico sotto rumore
correlato, e ne ha concluso che il limite appartiene all'informazione contenuta nella
sindrome. La conclusione ha un difetto: tutti e tre i bracci contengono LA STESSA rete
--- MLPClassifier(128,64) addestrato sugli stessi 4.8e5 campioni. Che convergano puo'
significare soltanto "questo e' quanto estrae questa rete".

Per distinguere le due letture servono metodi piu' potenti dello stesso MLP. Se scendono
sotto il pavimento, esso e' del modello; se non lo scalfiscono, e' dell'informazione.

  A) RETE GRANDE      MLP (512,256,128) invece di (128,64): ~40x i parametri. Se il
     vincolo fosse la capacita', qui si vedrebbe.

  B) TABELLA EMPIRICA  il decoder a massima verosimiglianza stimato dai dati: per ogni
     sindrome osservata in addestramento si predice l'osservabile di maggioranza; per le
     sindromi mai viste si ricade sul MWPM. E' il miglior decoder possibile DATI QUEI
     CAMPIONI, senza alcuna assunzione di modello ne' limite di capacita': non ha
     parametri da stimare, memorizza. Se nemmeno lui scende, il pavimento e' reale nel
     senso forte --- non c'e' altro da sapere in quella sindrome, a quella numerosita'.

     Va riportata anche la COPERTURA: la frazione di shot di test la cui sindrome era
     gia' stata osservata. Se e' bassa la tabella e' per lo piu' MWPM travestito e il
     confronto non dice nulla; se e' alta il confronto e' informativo. E' la diagnostica
     che rende il braccio B interpretabile anziche' solo suggestivo.

Uso (WSL, quantum-env):
    ~/quantum-env/bin/python controllo_pavimento.py
"""
import argparse
import json
import time
from collections import defaultdict
from datetime import datetime

import numpy as np
from sklearn.neural_network import MLPClassifier

from qec_neural_decoder import (
    build_circuit, with_crosstalk, sample, matcher, mwpm_predict, train_nn,
    binom_se, P_PHYS,
)
from confronto_bposd import PCT_LIST
from residuo_su_bposd import mcnemar, residuo, FRAC_TRAIN, FRAC_VAL


def train_nn_grande(X, y, seed):
    """Stessa ricetta di train_nn ma con ~40 volte i parametri. Se il pavimento fosse
    imposto dalla capacita' del modello, questa rete lo sfonderebbe."""
    nn = MLPClassifier(
        hidden_layer_sizes=(512, 256, 128),
        activation='relu', alpha=1e-5, batch_size=4096,
        learning_rate_init=3e-3, max_iter=200,
        early_stopping=True, n_iter_no_change=10, validation_fraction=0.1,
        random_state=seed,
    )
    nn.fit(X.astype(np.float32), y)
    return nn


def tabella_empirica(det_tr, y_tr, det_te, fallback_te):
    """Decoder a massima verosimiglianza stimato dai dati.

    Per ogni sindrome vista in addestramento memorizza l'osservabile di maggioranza; per
    le sindromi mai viste ricade sulla predizione del MWPM. Non stima parametri: e' il
    limite superiore di qualunque metodo che usi SOLO la sindrome, a quella numerosita'.
    """
    conteggi = defaultdict(lambda: [0, 0])
    for chiave, y in zip(map(bytes, np.packbits(det_tr, axis=1)), y_tr):
        conteggi[chiave][int(y)] += 1

    tavola = {k: (v[1] > v[0]) for k, v in conteggi.items()}
    pred = np.array(fallback_te, dtype=bool).copy()
    visto = np.zeros(det_te.shape[0], dtype=bool)
    for i, chiave in enumerate(map(bytes, np.packbits(det_te, axis=1))):
        if chiave in tavola:
            pred[i] = tavola[chiave]
            visto[i] = True
    return pred, float(visto.mean()), len(tavola)


def run_punto(d, p, p_ct, shots, seed):
    t0 = time.time()
    circ_nom = build_circuit(d, p)
    det, y = sample(with_crosstalk(circ_nom, p_ct), shots, seed)

    n_tr, n_va = int(shots * FRAC_TRAIN), int(shots * FRAC_VAL)
    tr, va, te = slice(0, n_tr), slice(n_tr, n_tr + n_va), slice(n_tr + n_va, None)
    y_te = y[te]
    n_te = len(y_te)

    pred_mwpm = mwpm_predict(matcher(circ_nom), det)

    # --- il pavimento di E10, ricalcolato qui per confronto sugli stessi shot ---
    fin_res, _, _ = residuo(det, pred_mwpm, y, tr, va, te, seed)
    rete = train_nn(det[tr], y[tr], seed)
    pred_rete = rete.predict_proba(det[te].astype(np.float32))[:, 1] >= 0.5

    # --- A) rete grande, sia da sola sia come residuo ---
    grande = train_nn_grande(det[tr], y[tr], seed)
    pred_grande = grande.predict_proba(det[te].astype(np.float32))[:, 1] >= 0.5

    X = np.concatenate([det, pred_mwpm[:, None]], axis=1)
    err = (pred_mwpm != y)
    gres = train_nn_grande(X[tr], err[tr], seed)
    pe_va = gres.predict_proba(X[va].astype(np.float32))[:, 1]
    soglie = list(np.round(np.arange(0.10, 0.96, 0.05), 2)) + [1.01]
    punteggi = {t: float(((pred_mwpm[va] ^ (pe_va >= t)) != y[va]).mean()) for t in soglie}
    thr = min(punteggi, key=punteggi.get)
    fin_grande = pred_mwpm[te] ^ (gres.predict_proba(X[te].astype(np.float32))[:, 1] >= thr)

    # --- B) tabella empirica ---
    pred_tab, copertura, n_sindromi = tabella_empirica(det[tr], y[tr], det[te],
                                                       pred_mwpm[te])

    e = {
        'mwpm': pred_mwpm[te] != y_te,
        'rete_sola': pred_rete != y_te,
        'mwpm_res': fin_res != y_te,
        'rete_grande': pred_grande != y_te,
        'mwpm_res_grande': fin_grande != y_te,
        'tabella': pred_tab != y_te,
    }
    pL = {k: float(v.mean()) for k, v in e.items()}
    pavimento = float(np.mean([pL['rete_sola'], pL['mwpm_res']]))

    return {
        'd': d, 'p': p, 'p_crosstalk': p_ct, 'shots': shots, 'seed': seed,
        'n_detectors': int(det.shape[1]), 'n_test': n_te,
        'pL': pL, 'pL_se': {k: binom_se(v, n_te) for k, v in pL.items()},
        'pavimento_E10': pavimento,
        'scarto_dal_pavimento': {k: (pavimento - v) / pavimento
                                 for k, v in pL.items()
                                 if k in ('rete_grande', 'mwpm_res_grande', 'tabella')},
        'tabella_copertura': copertura, 'tabella_sindromi_distinte': n_sindromi,
        'mcnemar_grande_vs_res': mcnemar(e['mwpm_res'], e['mwpm_res_grande']),
        'mcnemar_tabella_vs_res': mcnemar(e['mwpm_res'], e['tabella']),
        'secs': round(time.time() - t0, 1),
    }


def main():
    ap = argparse.ArgumentParser(description="M10/E11 — il pavimento e' della sindrome?")
    ap.add_argument('--shots', type=int, default=800_000)
    ap.add_argument('--distances', type=int, nargs='+', default=[3])
    args = ap.parse_args()

    t0 = time.time()
    print("=" * 78)
    print("E11 — IL PAVIMENTO DI E10 E' DELL'INFORMAZIONE O DELLA RETE?")
    print("    metodi piu' potenti dello stesso MLP: se scendono, il pavimento e' del modello")
    print("=" * 78)

    out = {'milestone': 'M10_controllo_pavimento', 'timestamp': datetime.now().isoformat(),
           'p_phys': P_PHYS, 'shots_per_config': args.shots, 'points': []}

    for d in args.distances:
        for i, pct in enumerate(PCT_LIST):
            r = run_punto(d, P_PHYS, pct, args.shots, seed=11_000 + d * 100 + i)
            s = r['scarto_dal_pavimento']
            print(f"  d={d} p_ct={pct:<6g}  pavimento={r['pavimento_E10']:.5f}\n"
                  f"        rete grande sola={r['pL']['rete_grande']:.5f} ({s['rete_grande']*100:+.1f}%)  "
                  f"residuo grande={r['pL']['mwpm_res_grande']:.5f} ({s['mwpm_res_grande']*100:+.1f}%)\n"
                  f"        tabella empirica={r['pL']['tabella']:.5f} ({s['tabella']*100:+.1f}%)  "
                  f"copertura {r['tabella_copertura']*100:.1f}%, "
                  f"{r['tabella_sindromi_distinte']} sindromi distinte   [{r['secs']}s]",
                  flush=True)
            out['points'].append(r)
            with open(f"results_M10_controllo_{datetime.now():%Y%m%d}.json", 'w') as f:
                json.dump(out, f, indent=2)

    print(f"\nTempo totale: {(time.time()-t0)/60:.1f} min")


if __name__ == '__main__':
    main()
