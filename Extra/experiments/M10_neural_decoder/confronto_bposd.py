"""M10/E7 — il guadagno della rete sopravvive a un decoder analitico migliore di MWPM?

E' il controllo piu' severo che si possa opporre al risultato di M10. Il decoder ibrido
batte il MWPM in presenza di crosstalk perche' il grafo di matching non puo' rappresentare
correlazioni fra qubit di dato adiacenti. Ma il MWPM non e' il miglior decoder analitico
disponibile: BP+OSD (belief propagation con ordered statistics decoding) lavora
direttamente sulla matrice di parita' del detector error model, senza richiedere che gli
errori siano decomponibili in archi, e puo' quindi rappresentare classi di errore che il
matching non rappresenta.

Se BP+OSD gestisse gia' bene il crosstalk, il guadagno attribuito all'apprendimento
sarebbe in realta' un guadagno attribuibile alla scelta di un decoder analitico migliore,
e il risultato di M10 andrebbe ridimensionato. Il confronto e' quindi doveroso, e il suo
esito e' informativo in entrambe le direzioni.

Nota: BP+OSD e' interrogato con la stessa mis-informazione del MWPM, cioe' con il DEM
NOMINALE (senza crosstalk), perche' e' quello che un decoder reale avrebbe a
disposizione. Il crosstalk e' presente nel circuito campionato ma assente dal modello.

Uso:
    python confronto_bposd.py --shots 50000 --distances 3 5
"""
import argparse
import json
import time
from datetime import datetime

import numpy as np
from ldpc import BpOsdDecoder
from ldpc.ckt_noise import detector_error_model_to_check_matrices

from qec_neural_decoder import (
    build_circuit, with_crosstalk, sample, matcher, mwpm_predict, P_PHYS,
)

PCT_LIST = [0.0, 0.005, 0.01, 0.02, 0.04]


def bposd_da_dem(dem, osd_order=10):
    """Costruisce un decoder BP+OSD dal detector error model.

    Il DEM fornisce la matrice di parita' (detector x meccanismi di errore), il vettore
    delle probabilita' di ciascun meccanismo e la matrice che lega i meccanismi agli
    osservabili logici. BP propaga le credenze sul grafo di Tanner; OSD interviene quando
    BP non converge, risolvendo esattamente su un sottoinsieme di colonne ordinate per
    affidabilita'.
    """
    m = detector_error_model_to_check_matrices(dem)
    dec = BpOsdDecoder(
        m.check_matrix,
        error_channel=list(m.priors),
        max_iter=30,
        bp_method='product_sum',
        osd_method='osd_cs',
        osd_order=osd_order,
    )
    return dec, m


def bposd_predict(dec, m, det):
    """Predizione dell'osservabile logico per ciascuno shot."""
    out = np.zeros(det.shape[0], dtype=bool)
    for i in range(det.shape[0]):
        e = dec.decode(det[i].astype(np.uint8))
        out[i] = bool((m.observables_matrix @ e) % 2)
    return out


def run_punto(d, p, p_ct, shots, seed):
    t0 = time.time()
    circ_nom = build_circuit(d, p)                 # modello NOMINALE, senza crosstalk
    circ_real = with_crosstalk(circ_nom, p_ct)     # circuito REALE, con crosstalk
    det, obs = sample(circ_real, shots, seed)

    # entrambi i decoder analitici ricevono il medesimo modello nominale
    dem_nom = circ_nom.detector_error_model(decompose_errors=True)
    m_mwpm = matcher(circ_nom)
    pred_mwpm = mwpm_predict(m_mwpm, det)

    dec, mats = bposd_da_dem(dem_nom)
    t_bp = time.time()
    pred_bposd = bposd_predict(dec, mats, det)
    secs_bposd = time.time() - t_bp

    def pl(pred):
        err = (pred != obs)
        v = float(err.mean())
        return v, float((v * (1 - v) / err.size) ** 0.5)

    pL_mwpm, se_mwpm = pl(pred_mwpm)
    pL_bposd, se_bposd = pl(pred_bposd)

    # Test di McNemar: i due decoder vedono gli STESSI shot, quindi il confronto e'
    # appaiato ed e' molto piu' sensibile di quello fra due errori indipendenti.
    err_m = (pred_mwpm != obs)
    err_b = (pred_bposd != obs)
    b = int((err_b & ~err_m).sum())      # BP+OSD sbaglia dove MWPM azzecca
    c = int((err_m & ~err_b).sum())      # BP+OSD azzecca dove MWPM sbaglia
    chi2 = (abs(b - c) - 1) ** 2 / (b + c) if (b + c) > 0 else 0.0
    from math import erfc, sqrt
    p_mcnemar = erfc(sqrt(chi2 / 2)) if chi2 > 0 else 1.0

    return {
        'd': d, 'p': p, 'p_crosstalk': p_ct, 'shots': shots, 'seed': seed,
        'pL_mwpm': pL_mwpm, 'pL_mwpm_se': se_mwpm,
        'pL_bposd': pL_bposd, 'pL_bposd_se': se_bposd,
        'guadagno_bposd_vs_mwpm': pL_mwpm / pL_bposd if pL_bposd else float('nan'),
        'mcnemar': {'b_bposd_peggiora': b, 'c_bposd_migliora': c,
                    'chi2': chi2, 'p_value': p_mcnemar},
        'secs_bposd': secs_bposd, 'secs': time.time() - t0,
    }


def main():
    ap = argparse.ArgumentParser(description="M10/E7 — BP+OSD contro MWPM sotto crosstalk")
    ap.add_argument('--shots', type=int, default=50_000)
    ap.add_argument('--distances', type=int, nargs='+', default=[3, 5])
    args = ap.parse_args()

    print("=" * 88)
    print("E7 — BP+OSD contro MWPM: il decoder analitico migliore gestisce il crosstalk?")
    print(f"    p fisico = {P_PHYS}; entrambi i decoder ricevono il DEM nominale")
    print("=" * 88)
    print(f"{'d':>2} {'p_ct':>7} {'MWPM':>10} {'BP+OSD':>10} {'BP+OSD/MWPM':>13} "
          f"{'McNemar':>11} {'s':>6}")

    out = {'milestone': 'M10_confronto_bposd', 'timestamp': datetime.now().isoformat(),
           'p_phys': P_PHYS, 'shots_per_config': args.shots, 'points': []}

    for d in args.distances:
        for i, pct in enumerate(PCT_LIST):
            r = run_punto(d, P_PHYS, pct, args.shots, seed=7000 + d * 100 + i)
            out['points'].append(r)
            print(f"{r['d']:>2} {pct:>7g} {r['pL_mwpm']:>10.5f} {r['pL_bposd']:>10.5f} "
                  f"{r['guadagno_bposd_vs_mwpm']:>13.3f} "
                  f"{r['mcnemar']['p_value']:>11.2e} {r['secs']:>6.0f}", flush=True)

    vinte = sum(1 for r in out['points']
                if r['pL_bposd'] < r['pL_mwpm'] - 2 * (
                    r['pL_bposd_se'] ** 2 + r['pL_mwpm_se'] ** 2) ** 0.5)
    out['bposd_batte_mwpm_2sigma'] = vinte
    print(f"\nFLAG E7: BP+OSD batte MWPM (oltre 2 sigma) in {vinte}/{len(out['points'])} "
          f"configurazioni")

    fname = f"results_M10_bposd_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(fname, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    print(f"Risultati salvati in: {fname}")


if __name__ == '__main__':
    main()
