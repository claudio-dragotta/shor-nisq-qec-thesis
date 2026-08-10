"""
pavimento_comune.py — Milestone M10, esperimento E10: esiste un pavimento comune?

E8 ha rilevato che il residuo appreso costruito sopra il matching e quello costruito sopra
BP+OSD atterrano sullo stesso errore logico entro l'1%, pur partendo da decoder che a
crosstalk nullo differiscono del 18%. Rileggendo E4 accanto a E8 si nota che anche la rete
usata da SOLA --- senza alcun decoder analitico sotto --- cade nello stesso intervallo.

Se il fatto regge, l'enunciato non e' "il residuo cancella la scelta del decoder di base"
ma qualcosa di piu' forte: il pavimento e' una proprieta' dell'informazione contenuta nella
sindrome, e non del metodo che la decodifica. Sotto crosstalk tutti questi metodi
estraggono la stessa quantita' di informazione e incontrano lo stesso limite.

Il confronto fatto finora e' pero' fra campagne diverse, con seed diversi, e la variazione
run-to-run e' dello stesso ordine dello scarto da misurare (a d=3, p_ct=0.01, pL_mwpm vale
0.05829 in E4 e 0.05908 in E8: 1.3% di differenza fra due stime dello stesso numero). Un
confronto a quella precisione non e' concludente. Qui i sei bracci girano SUGLI STESSI
CAMPIONI, il che rende ogni differenza appaiata e verificabile con McNemar.

I SEI BRACCI, in ordine di informazione utilizzata:
  1. banale        predice sempre "nessun flip logico" --- il tasso di base, soffitto
  2. rete sola     nessun modello analitico: la rete legge la sindrome e decide
  3. MWPM          matching di peso minimo sul modello nominale
  4. BP+OSD        propagazione di credenze + OSD sullo stesso modello nominale
  5. MWPM + res    il residuo appreso sopra il matching (l'ibrido di E4)
  6. BP+OSD + res  il residuo appreso sopra BP+OSD (il combinato di E8)

PREVISIONE REGISTRATA: i bracci 2, 5 e 6 coincidono entro l'errore statistico, mentre 3 e 4
stanno nettamente sopra. L'esito contrario --- il braccio 2 significativamente peggiore dei
bracci 5 e 6 --- direbbe che il decoder analitico contribuisce informazione che la rete da
sola non ricava, e il "pavimento comune" sarebbe un artefatto del confronto fra campagne.

Uso (WSL, quantum-env):
    ~/quantum-env/bin/python pavimento_comune.py --distances 3
"""
import argparse
import json
import time
from datetime import datetime

import numpy as np

from qec_neural_decoder import (
    build_circuit, with_crosstalk, sample, matcher, mwpm_predict, train_nn,
    binom_se, P_PHYS,
)
from confronto_bposd import PCT_LIST
from residuo_su_bposd import bposd_predict_par, mcnemar, residuo, FRAC_TRAIN, FRAC_VAL


def run_punto(d, p, p_ct, shots, seed, processi):
    t0 = time.time()
    circ_nom = build_circuit(d, p)
    circ_real = with_crosstalk(circ_nom, p_ct)
    det, y = sample(circ_real, shots, seed)

    n_tr, n_va = int(shots * FRAC_TRAIN), int(shots * FRAC_VAL)
    tr, va, te = slice(0, n_tr), slice(n_tr, n_tr + n_va), slice(n_tr + n_va, None)
    y_te = y[te]
    n_te = len(y_te)

    pred_mwpm = mwpm_predict(matcher(circ_nom), det)
    dem_nom = circ_nom.detector_error_model(decompose_errors=True)
    pred_bposd = bposd_predict_par(dem_nom, det, processi)

    # braccio 2: la rete come decoder autonomo, addestrata a predire l'osservabile
    rete = train_nn(det[tr], y[tr], seed)
    pred_rete = rete.predict_proba(det[te].astype(np.float32))[:, 1] >= 0.5

    fin_m, _, flip_m = residuo(det, pred_mwpm, y, tr, va, te, seed)
    fin_b, _, flip_b = residuo(det, pred_bposd, y, tr, va, te, seed + 1)

    err = {
        'banale': y_te.astype(bool),          # predizione costante 0 -> sbaglia dove y=1
        'rete_sola': pred_rete != y_te,
        'mwpm': pred_mwpm[te] != y_te,
        'bposd': pred_bposd[te] != y_te,
        'mwpm_res': fin_m != y_te,
        'bposd_res': fin_b != y_te,
    }
    pL = {k: float(v.mean()) for k, v in err.items()}

    # Il pavimento e' la media dei tre bracci che dovrebbero coincidere; la dispersione
    # relativa fra loro e' la quantita' che decide l'esito dell'esperimento.
    fondo = [pL['rete_sola'], pL['mwpm_res'], pL['bposd_res']]
    dispersione = (max(fondo) - min(fondo)) / np.mean(fondo)

    return {
        'd': d, 'p': p, 'p_crosstalk': p_ct, 'shots': shots, 'seed': seed,
        'n_detectors': int(det.shape[1]), 'n_test': n_te,
        'pL': pL, 'pL_se': {k: binom_se(v, n_te) for k, v in pL.items()},
        'pavimento_medio': float(np.mean(fondo)),
        'dispersione_relativa': float(dispersione),
        'ribalta': {'su_mwpm': flip_m, 'su_bposd': flip_b},
        # i due confronti appaiati che decidono: la rete da sola e' davvero equivalente
        # ai due ibridi, oppure e' significativamente peggiore?
        'mcnemar_rete_vs_mwpm_res': mcnemar(err['mwpm_res'], err['rete_sola']),
        'mcnemar_rete_vs_bposd_res': mcnemar(err['bposd_res'], err['rete_sola']),
        'secs': round(time.time() - t0, 1),
    }


def fmt(r):
    p = r['pL']
    return (f"  d={r['d']} p_ct={r['p_crosstalk']:<6g}\n"
            f"        banale={p['banale']:.5f}  MWPM={p['mwpm']:.5f}  "
            f"BP+OSD={p['bposd']:.5f}\n"
            f"        rete sola={p['rete_sola']:.5f}  MWPM+res={p['mwpm_res']:.5f}  "
            f"BP+OSD+res={p['bposd_res']:.5f}\n"
            f"        pavimento {r['pavimento_medio']:.5f}, dispersione fra i tre "
            f"{r['dispersione_relativa']*100:.2f}%  |  rete vs MWPM+res: "
            f"p={r['mcnemar_rete_vs_mwpm_res']['p_value']:.1e}   [{r['secs']}s]")


def main():
    ap = argparse.ArgumentParser(description="M10/E10 — il pavimento comune")
    ap.add_argument('--shots', type=int, default=800_000)
    ap.add_argument('--distances', type=int, nargs='+', default=[3])
    ap.add_argument('--processi', type=int, default=16)
    args = ap.parse_args()

    t0 = time.time()
    print("=" * 78)
    print("E10 — SEI DECODER, UN SOLO PAVIMENTO?")
    print(f"    p fisico = {P_PHYS}, {args.shots} shot per configurazione, tutti i bracci")
    print("    sugli stessi campioni. Previsione: rete sola == MWPM+res == BP+OSD+res")
    print("=" * 78)

    out = {'milestone': 'M10_pavimento_comune', 'timestamp': datetime.now().isoformat(),
           'p_phys': P_PHYS, 'shots_per_config': args.shots, 'points': []}

    for d in args.distances:
        for i, pct in enumerate(PCT_LIST):
            r = run_punto(d, P_PHYS, pct, args.shots, seed=10_000 + d * 100 + i,
                          processi=args.processi)
            print(fmt(r), flush=True)
            out['points'].append(r)
            with open(f"results_M10_pavimento_{datetime.now():%Y%m%d}.json", 'w') as f:
                json.dump(out, f, indent=2)

    concordi = sum(1 for r in out['points'] if r['dispersione_relativa'] < 0.03)
    out['punti_con_pavimento_entro_3pc'] = concordi
    print(f"\nFLAG E10: i tre bracci di fondo coincidono entro il 3% in "
          f"{concordi}/{len(out['points'])} configurazioni")
    print(f"Tempo totale: {(time.time()-t0)/60:.1f} min")


if __name__ == '__main__':
    main()
