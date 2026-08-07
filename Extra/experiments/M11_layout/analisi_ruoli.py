"""
analisi_ruoli.py — analisi corretta di M11b.

PERCHE' SERVE. test_ruoli.py imponeva initial_layout per collocare il registro di conteggio
sui qubit a readout migliore o peggiore. Il controllo di sanita' incluso nello script mostra
pero' che la manipolazione riesce solo in circa meta' dei casi: il ROUTING inserisce SWAP che
permutano i qubit, sicche' il qubit che porta il conteggio AL MOMENTO DELLA MISURA non e'
quello a cui era stato assegnato. Il confronto fra le due strategie intenzionali non testa
quindi l'ipotesi.

COSA SI FA INVECE. Si abbandona l'intervento e si usa la grandezza EFFETTIVAMENTE misurata:
il readout medio dei qubit su cui le misure sono realmente cadute. La domanda diventa

    a sottografo fissato, il readout dei qubit realmente misurati predice il successo?

Il controllo per sottografo si ottiene centrando entrambe le variabili sulla media del proprio
sottografo (correlazione parziale sui residui): elimina l'effetto di quale gruppo di qubit sia
stato usato, e isola l'effetto del ruolo al suo interno.

Uso: ~/quantum-env/bin/python analisi_ruoli.py
"""
import glob
import json

import numpy as np


def spearman(x, y):
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def main():
    d = json.load(open(sorted(glob.glob('results_M11b_ruoli_*.json'))[-1]))
    righe = d['righe']

    ro, ps, ecr, gruppo = [], [], [], []
    for g, r in enumerate(righe):
        for nome, v in r['strategie'].items():
            ro.append(v['readout_misurati']); ps.append(v['P_success'])
            ecr.append(v['n_ecr']); gruppo.append(g)
    ro, ps, ecr, gruppo = map(np.array, (ro, ps, ecr, gruppo))
    print(f"Esecuzioni totali: {len(ps)} su {len(righe)} sottografi\n")

    # --- centratura entro sottografo: isola la variazione DOVUTA AL RUOLO ---
    def centra(v):
        out = np.empty_like(v, dtype=float)
        for g in np.unique(gruppo):
            m = gruppo == g
            out[m] = v[m] - v[m].mean()
        return out

    ro_c, ps_c, ecr_c = centra(ro), centra(ps), centra(ecr)

    print("=== Correlazione GREZZA (fra tutti i punti, sottografi confusi) ===")
    print(f"  readout misurati  vs P_success : Spearman {spearman(ro, ps):+.3f}")
    print(f"  porte ECR         vs P_success : Spearman {spearman(ecr, ps):+.3f}")

    print("\n=== Correlazione PARZIALE (centrata entro sottografo) ===")
    print("    isola l'effetto del RUOLO, a parita' di gruppo di qubit fisici")
    print(f"  readout misurati  vs P_success : Spearman {spearman(ro_c, ps_c):+.3f}")
    print(f"  porte ECR         vs P_success : Spearman {spearman(ecr_c, ps_c):+.3f}")

    # --- quanto e' ampia la variazione entro sottografo? ---
    dentro = np.array([ps[gruppo == g].max() - ps[gruppo == g].min()
                       for g in np.unique(gruppo)])
    print(f"\n=== Ampiezza della forbice ENTRO sottografo (solo ruoli) ===")
    print(f"  media {dentro.mean():.4f} | mediana {np.median(dentro):.4f} | max {dentro.max():.4f}")

    # --- il ruolo migliore entro sottografo e' quello a readout piu' basso? ---
    ok = 0
    for g in np.unique(gruppo):
        m = gruppo == g
        ok += int(np.argmin(ro[m]) == np.argmax(ps[m]))
    print(f"  sottografi in cui il readout piu' basso da' anche il successo massimo: "
          f"{ok}/{len(np.unique(gruppo))} (atteso per caso: "
          f"{len(np.unique(gruppo))/5:.1f})")

    # --- confronto fra strategie, medie ---
    print("\n=== Media per strategia ===")
    nomi = sorted({k for r in righe for k in r['strategie']})
    for n in nomi:
        v = np.array([r['strategie'][n]['P_success'] for r in righe if n in r['strategie']])
        e = np.array([r['strategie'][n]['n_ecr'] for r in righe if n in r['strategie']])
        print(f"  {n:<20} P_success {v.mean():.4f} +/- {v.std(ddof=1)/np.sqrt(len(v)):.4f}"
              f"   ECR medi {e.mean():.0f}")

    out = {
        'nota': 'analisi correlazionale: la manipolazione via initial_layout non regge al routing',
        'n_run': int(len(ps)), 'n_sottografi': int(len(righe)),
        'spearman_grezzo_readout': spearman(ro, ps),
        'spearman_grezzo_ecr': spearman(ecr, ps),
        'spearman_parziale_readout': spearman(ro_c, ps_c),
        'spearman_parziale_ecr': spearman(ecr_c, ps_c),
        'forbice_entro_sottografo_media': float(dentro.mean()),
        'forbice_entro_sottografo_max': float(dentro.max()),
        'n_readout_min_coincide_con_successo_max': int(ok),
    }
    json.dump(out, open('analisi_ruoli.json', 'w'), indent=2)
    print("\nSalvato: analisi_ruoli.json")


if __name__ == '__main__':
    main()
