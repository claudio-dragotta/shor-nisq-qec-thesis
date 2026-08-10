"""
residuo_su_bposd.py — Milestone M10, esperimento E8: il residuo appreso sopra BP+OSD.

E7 ha stabilito che le due sorgenti di guadagno agiscono su assi opposti rispetto al
crosstalk: BP+OSD rende il massimo quando il modello di rumore che riceve e' corretto e
si degrada man mano che diventa incompleto; il residuo appreso rende zero a modello
corretto e cresce quanto piu' il modello si allontana dal dispositivo. E7 ha concluso che
le due cose sono "sommabili" e ha rinviato la verifica. Questo e' quella verifica.

La domanda non e' "quanto si guadagna" ma QUALE DEI DUE MECCANISMI opera, e le due
risposte possibili sono distinguibili in anticipo:

  ipotesi MOLTIPLICATIVA — i due decoder sbagliano su insiemi in larga parte disgiunti,
    e il residuo appreso trova sopra BP+OSD la stessa struttura che trovava sopra il
    matching. Allora il guadagno combinato approssima il prodotto dei due.

  ipotesi di SATURAZIONE — cio' che il residuo appreso recuperava sopra il matching era
    in buona parte gia' recuperabile da un decoder analitico piu' espressivo. Allora
    sopra BP+OSD la rete trova poco o nulla, il guadagno combinato collassa su quello di
    BP+OSD da solo, e l'ortogonalita' affermata in E7 non regge.

La seconda e' l'esito sfavorevole al risultato della tesi, ed e' dichiarata prima di
eseguire: e' cio' che rende questo un controllo e non una conferma.

Un terzo esito e' possibile e nessuna delle due ipotesi lo prevede: che il residuo renda
sopra BP+OSD PIU' di quanto rendesse sopra il matching. Avrebbe una spiegazione precisa
--- sotto crosstalk BP+OSD sbaglia piu' del matching (E7), e sbaglia perche' si fida piu'
a fondo di un modello errato, il che produce fallimenti sistematici e quindi piu'
apprendibili di quelli del matching.

Rispetto a E4 ed E7 questo esperimento misura i quattro bracci SUGLI STESSI SHOT, il che
elimina il disallineamento fra le due campagne precedenti (che usavano 8e5 e 2e5 campioni
con seed diversi: a d=3, p_ct=0, pL_mwpm risultava 0.00415 in una e 0.00428 nell'altra).

Uso (WSL, quantum-env):
    ~/quantum-env/bin/python residuo_su_bposd.py --distances 3
    ~/quantum-env/bin/python residuo_su_bposd.py --distances 5 --shots 400000
"""
import argparse
import json
import math
import os
import time
from datetime import datetime
from multiprocessing import Pool

import numpy as np
import stim

from qec_neural_decoder import (
    build_circuit, with_crosstalk, sample, matcher, mwpm_predict, train_nn,
    binom_se, P_PHYS,
)
from confronto_bposd import bposd_da_dem, PCT_LIST

FRAC_TRAIN, FRAC_VAL = 0.60, 0.15
THRESHOLDS = list(np.round(np.arange(0.10, 0.96, 0.05), 2)) + [1.01]

_W = {}


def _init_worker(dem_str):
    """Ogni processo ricostruisce il proprio decoder: l'oggetto BpOsdDecoder non e'
    serializzabile, il detector error model come stringa si'."""
    dec, mats = bposd_da_dem(stim.DetectorErrorModel(dem_str))
    _W['dec'], _W['mats'] = dec, mats


def _decodifica_blocco(blocco):
    dec, mats = _W['dec'], _W['mats']
    out = np.zeros(blocco.shape[0], dtype=bool)
    for i in range(blocco.shape[0]):
        e = dec.decode(blocco[i].astype(np.uint8))
        out[i] = bool((mats.observables_matrix @ e) % 2)
    return out


def bposd_predict_par(dem, det, processi):
    """Come bposd_predict di E7, ma distribuita: ogni shot e' indipendente dagli altri,
    quindi il ciclo si spezza senza alcuna approssimazione. E' l'unico modo per portare
    d=5 su 8e5 campioni entro tempi ragionevoli (il decoder ldpc non espone un'API
    batch: si veda dir(BpOsdDecoder))."""
    blocchi = np.array_split(det, processi * 4)
    with Pool(processi, initializer=_init_worker, initargs=(str(dem),)) as pool:
        parti = pool.map(_decodifica_blocco, blocchi)
    return np.concatenate(parti)


def mcnemar(err_a, err_b):
    """a = riferimento, b = candidato. Restituisce quante volte il candidato peggiora,
    quante migliora, e la significativita' della differenza sulle coppie discordanti."""
    b = int((err_b & ~err_a).sum())
    c = int((~err_b & err_a).sum())
    chi2 = (b - c) ** 2 / (b + c) if (b + c) > 0 else 0.0
    return {'b_peggiora': b, 'c_migliora': c, 'chi2': float(chi2),
            'p_value': float(math.erfc(math.sqrt(chi2 / 2))) if chi2 > 0 else 1.0}


def residuo(det, pred, y, tr, va, te, seed):
    """La forma residuale di E4, indipendente dal decoder di base: la rete impara QUANDO
    ribaltare la predizione ricevuta, e la soglia di ribaltamento e' scelta in validazione.
    La soglia 1.01 ('non ribaltare mai') garantisce che l'ibrido non possa fare
    sistematicamente peggio del decoder su cui e' costruito."""
    X = np.concatenate([det, pred[:, None]], axis=1)
    err = (pred != y)
    nn = train_nn(X[tr], err[tr], seed)

    pe_va = nn.predict_proba(X[va].astype(np.float32))[:, 1]
    punteggi = {t: float(((pred[va] ^ (pe_va >= t)) != y[va]).mean()) for t in THRESHOLDS}
    thr = min(punteggi, key=punteggi.get)

    flip = nn.predict_proba(X[te].astype(np.float32))[:, 1] >= thr
    return pred[te] ^ flip, float(thr), float(flip.mean())


def run_punto(d, p, p_ct, shots, seed, processi):
    t0 = time.time()
    circ_nom = build_circuit(d, p)                 # il modello che l'operatore crede
    circ_real = with_crosstalk(circ_nom, p_ct)     # il dispositivo effettivo
    det, y = sample(circ_real, shots, seed)

    n_tr, n_va = int(shots * FRAC_TRAIN), int(shots * FRAC_VAL)
    tr, va, te = slice(0, n_tr), slice(n_tr, n_tr + n_va), slice(n_tr + n_va, None)
    y_te = y[te]
    n_te = len(y_te)

    # I due decoder analitici ricevono entrambi il modello NOMINALE: e' la condizione di
    # E7, e la sola realistica --- il crosstalk e' cio' che il modello non descrive.
    pred_mwpm = mwpm_predict(matcher(circ_nom), det)
    t_bp = time.time()
    dem_nom = circ_nom.detector_error_model(decompose_errors=True)
    pred_bposd = bposd_predict_par(dem_nom, det, processi)
    secs_bposd = time.time() - t_bp

    fin_m, thr_m, flip_m = residuo(det, pred_mwpm, y, tr, va, te, seed)
    fin_b, thr_b, flip_b = residuo(det, pred_bposd, y, tr, va, te, seed + 1)

    bracci = {
        'mwpm': pred_mwpm[te] != y_te,
        'bposd': pred_bposd[te] != y_te,
        'mwpm_nn': fin_m != y_te,
        'bposd_nn': fin_b != y_te,
    }
    pL = {k: float(v.mean()) for k, v in bracci.items()}

    g_bposd = pL['mwpm'] / pL['bposd'] if pL['bposd'] else float('nan')
    g_mwpm_nn = pL['mwpm'] / pL['mwpm_nn'] if pL['mwpm_nn'] else float('nan')
    g_comb = pL['mwpm'] / pL['bposd_nn'] if pL['bposd_nn'] else float('nan')

    return {
        'd': d, 'p': p, 'p_crosstalk': p_ct, 'shots': shots, 'seed': seed,
        'n_detectors': int(det.shape[1]), 'n_train': n_tr, 'n_val': n_va, 'n_test': n_te,
        'esempi_positivi_train_mwpm': int((pred_mwpm[tr] != y[tr]).sum()),
        'esempi_positivi_train_bposd': int((pred_bposd[tr] != y[tr]).sum()),
        'pL': pL,
        'pL_se': {k: binom_se(v, n_te) for k, v in pL.items()},
        'guadagni_vs_mwpm': {
            'bposd': g_bposd, 'mwpm_nn': g_mwpm_nn, 'bposd_nn': g_comb,
            # la previsione registrata in SviluppiFuturi: il combinato approssima il
            # prodotto dei due guadagni presi separatamente
            'prodotto_previsto': g_bposd * g_mwpm_nn,
            'scarto_dal_prodotto': g_comb - g_bposd * g_mwpm_nn,
        },
        'residuo': {'soglia_su_mwpm': thr_m, 'ribalta_su_mwpm': flip_m,
                    'soglia_su_bposd': thr_b, 'ribalta_su_bposd': flip_b},
        # il confronto che decide fra le due ipotesi: il residuo aggiunge qualcosa
        # SOPRA BP+OSD, oppure BP+OSD aveva gia' assorbito tutto?
        'mcnemar_bposd_nn_vs_bposd': mcnemar(bracci['bposd'], bracci['bposd_nn']),
        'mcnemar_bposd_nn_vs_mwpm_nn': mcnemar(bracci['mwpm_nn'], bracci['bposd_nn']),
        'secs_bposd': round(secs_bposd, 1), 'secs': round(time.time() - t0, 1),
    }


def fmt(r):
    g = r['guadagni_vs_mwpm']
    m = r['mcnemar_bposd_nn_vs_bposd']
    return (f"  d={r['d']} p_ct={r['p_crosstalk']:<6g}  "
            f"MWPM={r['pL']['mwpm']:.5f}  BP+OSD={r['pL']['bposd']:.5f}  "
            f"MWPM+res={r['pL']['mwpm_nn']:.5f}  BP+OSD+res={r['pL']['bposd_nn']:.5f}\n"
            f"        guadagni vs MWPM: BP+OSD {g['bposd']:.3f}x  "
            f"MWPM+res {g['mwpm_nn']:.3f}x  COMBINATO {g['bposd_nn']:.3f}x  "
            f"(prodotto previsto {g['prodotto_previsto']:.3f}x, "
            f"scarto {g['scarto_dal_prodotto']:+.3f})\n"
            f"        il residuo ribalta il {r['residuo']['ribalta_su_bposd']*100:.2f}% "
            f"delle predizioni BP+OSD, McNemar p={m['p_value']:.1e}   [{r['secs']}s]")


def main():
    ap = argparse.ArgumentParser(description="M10/E8 — residuo appreso sopra BP+OSD")
    ap.add_argument('--shots', type=int, default=800_000)
    ap.add_argument('--distances', type=int, nargs='+', default=[3])
    ap.add_argument('--processi', type=int, default=max(1, (os.cpu_count() or 4) - 2))
    args = ap.parse_args()

    t0 = time.time()
    print("=" * 78)
    print("E8 — IL RESIDUO APPRESO SOPRA BP+OSD: le due sorgenti di guadagno si sommano?")
    print(f"    p fisico = {P_PHYS}, {args.shots} shot per configurazione, "
          f"{args.processi} processi")
    print("    ipotesi moltiplicativa: combinato ~ prodotto | saturazione: combinato ~ BP+OSD")
    print("=" * 78)

    out = {'milestone': 'M10_residuo_su_bposd', 'timestamp': datetime.now().isoformat(),
           'p_phys': P_PHYS, 'shots_per_config': args.shots,
           'frac_train': FRAC_TRAIN, 'frac_val': FRAC_VAL, 'points': []}

    for d in args.distances:
        for i, pct in enumerate(PCT_LIST):
            r = run_punto(d, P_PHYS, pct, args.shots, seed=8000 + d * 100 + i,
                          processi=args.processi)
            print(fmt(r), flush=True)
            out['points'].append(r)

            fname = f"results_M10_residuo_bposd_{datetime.now():%Y%m%d}.json"
            with open(fname, 'w') as f:      # salvataggio incrementale: una campagna a
                json.dump(out, f, indent=2)  # d=5 dura ore, non va persa a meta'

    vince = sum(1 for r in out['points']
                if r['pL']['bposd_nn'] < r['pL']['bposd']
                and r['mcnemar_bposd_nn_vs_bposd']['p_value'] < 0.01)
    out['residuo_batte_bposd'] = vince
    print(f"\nFLAG E8: il residuo migliora BP+OSD (p<0.01) in {vince}/{len(out['points'])} "
          f"configurazioni")
    print(f"Tempo totale: {(time.time()-t0)/60:.1f} min")


if __name__ == '__main__':
    main()
