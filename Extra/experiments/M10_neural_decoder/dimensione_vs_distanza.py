"""
dimensione_vs_distanza.py — Milestone M10, esperimento E9: perche' il residuo fallisce a d=7.

E4 ha rilevato che a distanza 7 il residuo appreso non ribalta alcuno shot. La tesi
attribuiva il fallimento alla scarsita' di esempi positivi (l'evento da apprendere e' il
fallimento del matching, la cui frequenza E' p_L, che decresce esponenzialmente con d).
Il conteggio degli esempi smentisce quella spiegazione: essa vale per la sola
configurazione senza crosstalk, mentre nelle altre quattro la rete dispone di 1.8e4-2.2e5
esempi positivi e continua a non intervenire. A numerosita' praticamente identica
(17 093 contro 17 796) il residuo interviene a d=5 e non a d=7.

Resta pero' un'ambiguita': fra quelle due configurazioni cambiano DUE cose insieme, la
distanza del codice (5 -> 7) e il numero di detector (120 -> 336). Questo esperimento le
separa, sfruttando il fatto che il numero di detector e' il prodotto fra gli stabilizzatori
per ciclo e il numero di cicli --- quindi si puo' variare a distanza fissa.

  d=7, rounds=3   ->  144 detector   distanza grande, ingresso piccolo
  d=7, rounds=7   ->  336 detector   (replica della configurazione fallita in E4)
  d=5, rounds=14  ->  336 detector   distanza piccola, ingresso grande
  d=5, rounds=5   ->  120 detector   (replica della configurazione riuscita in E4)

E' un incrocio 2x2. Le due ipotesi danno previsioni opposte sulle celle diagonali:

  ipotesi DIMENSIONE   il vincolo e' la larghezza dell'ingresso per una rete densa, che
    tratta i detector come dimensioni indipendenti. Previsione: il residuo interviene a
    (d=7, 144) e NON interviene a (d=5, 336). La distanza non conta di per se'.

  ipotesi DISTANZA     il vincolo e' qualcosa del reticolo grande --- per esempio che a
    d=7 il fallimento del matching dipenda da correlazioni cosi' estese da non essere
    apprendibili affatto. Previsione: il residuo NON interviene a (d=7, 144) e interviene
    a (d=5, 336).

Se entrambe le celle diagonali si comportano come la propria riga anziche' come la propria
colonna, nessuna delle due ipotesi regge e il fallimento va riattribuito.

AVVERTENZA sul controllo. Ridurre i cicli non lascia invariata la fisica: il crosstalk
viene iniettato meno volte, quindi p_L cala e con esso il numero di esempi positivi. Il
conteggio e' riportato per ogni cella proprio per verificare che resti abbondante: cio'
che l'esperimento controlla e' se il residuo INTERVIENE, non di quanto guadagni.

Uso (WSL, quantum-env):
    ~/quantum-env/bin/python dimensione_vs_distanza.py
"""
import argparse
import json
import time
from datetime import datetime

import numpy as np

from qec_neural_decoder import (
    build_circuit, with_crosstalk, sample, matcher, mwpm_predict, binom_se, P_PHYS,
)
from qec_hybrid_decoder import run_hybrid

# (distanza, cicli): le quattro celle dell'incrocio
CELLE = [(7, 3), (7, 7), (5, 14), (5, 5)]
PCT_LIST = [0.005, 0.02]      # i due livelli in cui a d=7 gli esempi positivi abbondano


def main():
    ap = argparse.ArgumentParser(description="M10/E9 — dimensione dell'ingresso o distanza?")
    ap.add_argument('--shots', type=int, default=800_000)
    args = ap.parse_args()

    t0 = time.time()
    print("=" * 78)
    print("E9 — IL FALLIMENTO A d=7: larghezza dell'ingresso o distanza del codice?")
    print(f"    p fisico = {P_PHYS}, {args.shots} shot per cella")
    print("    dimensione: interviene a (7,144) e non a (5,336) | distanza: il contrario")
    print("=" * 78)

    out = {'milestone': 'M10_dimensione_vs_distanza', 'timestamp': datetime.now().isoformat(),
           'p_phys': P_PHYS, 'shots_per_config': args.shots, 'points': []}

    for i, (d, rounds) in enumerate(CELLE):
        for j, pct in enumerate(PCT_LIST):
            r = run_hybrid_rounds(d, P_PHYS, args.shots, seed=9000 + i * 10 + j,
                                  p_ct=pct, rounds=rounds)
            print(f"  d={d} cicli={rounds:<2} det={r['n_detectors']:<4} p_ct={pct:<6g}  "
                  f"pos={r['esempi_positivi_train']:>7}  "
                  f"MWPM={r['pL_mwpm']:.5f}  IBRIDO={r['pL_hybrid']:.5f}  "
                  f"ribalta {r['flip_rate']*100:.2f}%  "
                  f"({'INTERVIENE' if r['flip_rate'] > 1e-4 else 'si astiene'})  "
                  f"[{r['secs']}s]", flush=True)
            out['points'].append(r)
            with open(f"results_M10_dimensione_{datetime.now():%Y%m%d}.json", 'w') as f:
                json.dump(out, f, indent=2, default=str)

    print(f"\nTempo totale: {(time.time()-t0)/60:.1f} min")


def run_hybrid_rounds(d, p, shots, seed, p_ct, rounds):
    """run_hybrid di E4 con il numero di cicli esposto, piu' il conteggio degli esempi
    positivi --- che e' la variabile di confondimento da tenere sotto controllo."""
    t0 = time.time()
    circ_nom = build_circuit(d, p, rounds=rounds)
    circ_real = with_crosstalk(circ_nom, p_ct)
    det, y = sample(circ_real, shots, seed)
    pred = mwpm_predict(matcher(circ_nom), det)

    n_tr = int(shots * 0.60)
    r = run_hybrid_da_campioni(det, y, pred, shots, seed)
    r.update({'d': d, 'rounds': rounds, 'p': p, 'p_crosstalk': p_ct, 'shots': shots,
              'seed': seed, 'n_detectors': int(det.shape[1]),
              'esempi_positivi_train': int((pred[:n_tr] != y[:n_tr]).sum()),
              'secs': round(time.time() - t0, 1)})
    return r


def run_hybrid_da_campioni(det, y, pred, shots, seed):
    """La parte di E4 che non dipende dal circuito: addestra il residuo, sceglie la soglia
    in validazione, la applica al test. Ripetuta qui per non ricampionare due volte."""
    from qec_hybrid_decoder import FRAC_TRAIN, FRAC_VAL, THRESHOLDS
    from qec_neural_decoder import train_nn

    n_tr, n_va = int(shots * FRAC_TRAIN), int(shots * FRAC_VAL)
    tr, va, te = slice(0, n_tr), slice(n_tr, n_tr + n_va), slice(n_tr + n_va, None)
    n_te = len(y[te])

    X = np.concatenate([det, pred[:, None]], axis=1)
    err = (pred != y)
    nn = train_nn(X[tr], err[tr], seed)

    pe_va = nn.predict_proba(X[va].astype(np.float32))[:, 1]
    punteggi = {t: float(((pred[va] ^ (pe_va >= t)) != y[va]).mean()) for t in THRESHOLDS}
    thr = min(punteggi, key=punteggi.get)

    flip = nn.predict_proba(X[te].astype(np.float32))[:, 1] >= thr
    final = pred[te] ^ flip
    pL_m = float((pred[te] != y[te]).mean())
    pL_h = float((final != y[te]).mean())
    return {'n_train': n_tr, 'n_val': n_va, 'n_test': n_te,
            'pL_mwpm': pL_m, 'pL_mwpm_se': binom_se(pL_m, n_te),
            'pL_hybrid': pL_h, 'pL_hybrid_se': binom_se(pL_h, n_te),
            'threshold': float(thr), 'flip_rate': float(flip.mean()),
            'gain_hybrid_vs_mwpm': (pL_m / pL_h) if pL_h > 0 else None}


if __name__ == '__main__':
    main()
