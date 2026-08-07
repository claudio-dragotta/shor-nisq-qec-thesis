"""
propaga_su_shor.py — collega il decoder ibrido (M10/E4) alla curva dello Shor logico (M8).

Chiude l'anello che in tesi era argomentato ma non misurato:

    decoder appreso  ->  errore logico piu' basso  ->  probabilita' di successo di Shor piu' alta

I due pezzi esistono gia': la curva P_success(p_L) di M8 e i p_L di MWPM e dell'ibrido di E4.
Qui si interpola la prima nei punti forniti dalla seconda. Non e' una nuova campagna: e' un
calcolo su dati gia' raccolti, e va dichiarato come tale in tesi.

Uso: ~/quantum-env/bin/python propaga_su_shor.py
"""
import glob
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
M8 = os.path.join(HERE, '..', 'M8_shor_logico')


def curva_shor():
    """P_success(p_L) da M8, in scala log10(p_L). Ancora a p_L->0 = limite dell'istanza."""
    f = sorted(glob.glob(os.path.join(M8, 'results_M8_shor_logico_*.json')))[-1]
    c = json.load(open(f))['curve']
    pts = [r for r in c['points'] if r['p_L'] > 0]
    x = np.log10([r['p_L'] for r in pts])
    y = np.array([r['P_success'] for r in pts])
    # ancora a p_L molto piccolo: P_success tende al limite intrinseco dell'istanza
    x = np.concatenate([[-6.0], x])
    y = np.concatenate([[c['P_ideal']], y])
    o = np.argsort(x)
    return x[o], y[o], c['P_ideal']


def main():
    x, y, p_ideal = curva_shor()
    P = lambda pl: float(np.interp(np.log10(pl), x, y))

    f = sorted(glob.glob(os.path.join(HERE, 'results_M10_hybrid_*.json')))[-1]
    pts = json.load(open(f))['points']

    print(f"Limite intrinseco dell'istanza (N=15, a=7): P_success = {p_ideal:.4f}\n")
    print("  d  p_ct    p_L MWPM   p_L ibrido |  P_succ MWPM  P_succ ibrido   guadagno")
    print("  " + "-" * 74)
    out = []
    for r in sorted(pts, key=lambda r: (r['d'], r['p_crosstalk'])):
        if r['p_crosstalk'] == 0:
            continue
        pm, ph = r['pL_mwpm'], r['pL_hybrid']
        Pm, Ph = P(pm), P(ph)
        d_pp = (Ph - Pm) * 100
        print(f"  {r['d']}  {r['p_crosstalk']:<6g}  {pm:.5f}    {ph:.5f}   |  "
              f"{Pm:.4f}       {Ph:.4f}       {d_pp:+.2f} p.p.")
        out.append({'d': r['d'], 'p_crosstalk': r['p_crosstalk'],
                    'pL_mwpm': pm, 'pL_hybrid': ph,
                    'P_success_mwpm': Pm, 'P_success_hybrid': Ph,
                    'delta_punti_percentuali': d_pp,
                    'mcnemar_p': r.get('mcnemar', {}).get('p_value')})

    best = max(out, key=lambda r: r['delta_punti_percentuali'])
    print(f"\n  Guadagno massimo: {best['delta_punti_percentuali']:+.2f} punti percentuali "
          f"(d={best['d']}, p_ct={best['p_crosstalk']})")
    print(f"  ovvero da P_success = {best['P_success_mwpm']:.4f} a {best['P_success_hybrid']:.4f}")

    dst = os.path.join(HERE, 'propagazione_su_shor.json')
    json.dump({'nota': 'interpolazione della curva M8 nei p_L di M10/E4; nessuna nuova simulazione',
               'P_ideal': p_ideal, 'punti': out}, open(dst, 'w'), indent=2)
    print(f"\nSalvato: {os.path.basename(dst)}")


if __name__ == '__main__':
    main()
