"""M10/E6 — decodifica con modello di rumore MIS-CALIBRATO: il caso d'uso reale.

Negli esperimenti E1-E4 il decoder MWPM riceve il detector error model generato da Stim
dal circuito stesso: un modello ESATTO del rumore. E' una condizione che su hardware
reale non si verifica mai. Il DEM di un decoder in produzione e' costruito a partire
dalla calibrazione del dispositivo — misurata a intervalli, soggetta a deriva, e
inevitabilmente diversa dal rumore effettivo al momento dell'esecuzione.

L'esperimento isola questa differenza. Il circuito e' campionato con il rumore reale, ma
il matching e' costruito su un DEM in cui l'errore di MISURA e' sbagliato di un fattore
(1+delta), mentre l'errore di gate resta corretto.

ATTENZIONE — la mis-calibrazione dev'essere NON UNIFORME. Un primo tentativo scalava
tutte le probabilita' di errore dello stesso fattore, e non produceva alcun effetto
(costo misurato 1.000, 1.004, 1.000 per delta = 0, +100%, -50%). La ragione e' che MWPM
minimizza il peso totale del matching, e il peso di un arco vale log((1-p)/p) ~ -log p:
scalare tutte le p per una costante trasla tutti i pesi della stessa quantita', lasciando
invariato il matching di peso minimo. Cio' che rende MWPM vulnerabile non e' sbagliare
la SCALA del rumore ma il suo BILANCIAMENTO — il rapporto fra archi temporali (errori di
misura) e archi spaziali (errori di dato), che e' esattamente cio' che questo script
perturba.

E' l'ipotesi centrale della tesi (l'apprendimento paga dove il modello analitico e'
strutturalmente cieco) applicata alla forma piu' comune di cecita': non un canale di
rumore assente dal modello, ma i pesi relativi sbagliati.

Uso:
    python decoder_miscalibrato.py --shots 400000 --distances 3 5
"""
import argparse
import json
import time
from datetime import datetime

import numpy as np
import pymatching
import stim

from qec_neural_decoder import (
    build_circuit, sample, mwpm_predict, train_nn, P_PHYS, BASIS,
)

FRAC_TRAIN, FRAC_VAL = 0.5, 0.2
# errore di misura creduto = reale * (1 + delta); errore di gate creduto = corretto
DELTA_LIST = [-0.8, -0.5, 0.0, 1.0, 3.0, 9.0]


def matcher_miscalibrato(d, p_gate, p_misura):
    """Matching su un DEM in cui errore di misura e di gate sono sbilanciati.

    p_gate resta quello vero; p_misura e' quello che il decoder *crede*. Il DEM che
    ne risulta assegna agli archi temporali un peso diverso da quello corretto, ed e'
    questo squilibrio — non un fattore di scala globale — a far sbagliare il matching.
    """
    circ = stim.Circuit.generated(
        f'surface_code:rotated_memory_{BASIS}',
        distance=d, rounds=d,
        after_clifford_depolarization=p_gate,
        after_reset_flip_probability=p_gate,
        before_measure_flip_probability=p_misura,
    )
    dem = circ.detector_error_model(decompose_errors=True)
    return pymatching.Matching.from_detector_error_model(dem)


def run_punto(d, p_reale, delta, shots, seed):
    t0 = time.time()
    p_creduto = p_reale * (1.0 + delta)      # errore di MISURA creduto dal decoder

    circ = build_circuit(d, p_reale)
    det, obs = sample(circ, shots, seed)

    # MWPM con bilanciamento sbagliato, e — come riferimento — con modello esatto
    m_sbagliato = matcher_miscalibrato(d, p_reale, p_creduto)
    m_esatto = matcher_miscalibrato(d, p_reale, p_reale)
    pred_sb = mwpm_predict(m_sbagliato, det)
    pred_ex = mwpm_predict(m_esatto, det)

    n_tr = int(FRAC_TRAIN * shots)
    n_val = int(FRAC_VAL * shots)
    tr = slice(0, n_tr)
    te = slice(n_tr + n_val, shots)

    nn = train_nn(det[tr], obs[tr], seed)
    pred_nn = nn.predict(det[te].astype(np.float32)).astype(bool)

    def pl(pred, sel):
        err = (pred[sel] != obs[sel])
        v = float(err.mean())
        return v, float((v * (1 - v) / err.size) ** 0.5)

    pL_sb, se_sb = pl(pred_sb, te)
    pL_ex, se_ex = pl(pred_ex, te)
    # ATTENZIONE: pred_nn ha la lunghezza del solo test set, obs quella di tutti gli
    # shot. Va confrontato con obs[te], non con obs[:len(pred_nn)] — che sarebbe la
    # porzione di addestramento, e produrrebbe un p_L privo di senso.
    err_nn = (pred_nn != obs[te])
    pL_nn = float(err_nn.mean())
    se_nn = float((pL_nn * (1 - pL_nn) / err_nn.size) ** 0.5)

    return {
        'd': d, 'p_reale': p_reale, 'delta': delta, 'p_misura_creduto': p_creduto,
        'shots': shots, 'seed': seed, 'n_test': int(shots - n_tr - n_val),
        'pL_mwpm_miscalibrato': pL_sb, 'pL_mwpm_miscalibrato_se': se_sb,
        'pL_mwpm_esatto': pL_ex, 'pL_mwpm_esatto_se': se_ex,
        'pL_nn': pL_nn, 'pL_nn_se': se_nn,
        'costo_miscalibrazione': pL_sb / pL_ex if pL_ex else float('nan'),
        'guadagno_nn_vs_miscalibrato': pL_sb / pL_nn if pL_nn else float('nan'),
        'secs': time.time() - t0,
    }


def main():
    ap = argparse.ArgumentParser(description="M10/E6 — decoder con DEM mis-calibrato")
    ap.add_argument('--shots', type=int, default=400_000)
    ap.add_argument('--distances', type=int, nargs='+', default=[3, 5])
    args = ap.parse_args()

    print("=" * 96)
    print("E6 — MWPM CON MODELLO DI RUMORE SBAGLIATO contro una rete che non usa modello")
    print(f"    p reale = {P_PHYS};  il decoder crede che l'errore di MISURA sia p*(1+delta)")
    print("=" * 96)
    print(f"{'d':>2} {'delta':>7} {'p_mis creduto':>13} {'MWPM esatto':>13} "
          f"{'MWPM sbagl.':>13} {'rete':>13} {'costo':>7} {'rete/sbagl.':>12}")

    out = {'milestone': 'M10_decoder_miscalibrato',
           'timestamp': datetime.now().isoformat(),
           'p_phys': P_PHYS, 'shots_per_config': args.shots, 'points': []}

    for d in args.distances:
        for i, delta in enumerate(DELTA_LIST):
            r = run_punto(d, P_PHYS, delta, args.shots, seed=6000 + d * 100 + i)
            out['points'].append(r)
            print(f"{r['d']:>2} {delta:>+7.0%} {r['p_misura_creduto']:>10.5f} "
                  f"{r['pL_mwpm_esatto']:>13.5f} {r['pL_mwpm_miscalibrato']:>13.5f} "
                  f"{r['pL_nn']:>13.5f} {r['costo_miscalibrazione']:>7.3f} "
                  f"{r['guadagno_nn_vs_miscalibrato']:>12.3f}", flush=True)

    vinte = sum(1 for r in out['points']
                if r['pL_nn'] < r['pL_mwpm_miscalibrato'] - 2 * (
                    r['pL_nn_se'] ** 2 + r['pL_mwpm_miscalibrato_se'] ** 2) ** 0.5)
    out['nn_batte_miscalibrato_2sigma'] = vinte
    print(f"\nFLAG E6: la rete batte MWPM mis-calibrato (oltre 2 sigma) in "
          f"{vinte}/{len(out['points'])} configurazioni")

    fname = f"results_M10_miscalibrato_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(fname, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    print(f"Risultati salvati in: {fname}")


if __name__ == '__main__':
    main()
