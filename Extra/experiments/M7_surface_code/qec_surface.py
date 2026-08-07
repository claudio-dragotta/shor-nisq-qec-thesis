"""
qec_surface.py — Milestone M7 (documento di indirizzo, §10): surface code.
Stima del logical error rate p_L con decoder reale (MWPM via PyMatching) su circuiti
generati da Stim, per distanze d = 3, 5, 7.

Flag di validazione (piano_azione_qec.md, Parte V — M7):
  - sanity: a p piccolo, d maggiore -> p_L minore;
  - FLAG DECISIVO: le curve d=3,5,7 si INCROCIANO a una soglia p_th (~0.5-1%);
  - sotto soglia d up => p_L down (soppressione), sopra soglia d up => p_L up.

Modello di rumore (circuit-level, come da esempio del documento):
  after_clifford_depolarization = after_reset_flip = before_measure_flip = p ; rounds = d.

Uso (WSL, quantum-env con stim+pymatching):
    python qec_surface.py                 # griglia d=3,5,7, base Z
    python qec_surface.py --basis x --shots 400000
"""
import argparse
import json
from datetime import datetime

import numpy as np
import stim
import pymatching


def logical_error_rate(d, p, shots, basis='z', rounds=None, seed=None):
    """p_L per un memory experiment del surface code ruotato.

    seed: passato a compile_detector_sampler, altrimenti il campionamento non e'
    riproducibile (il parametro era accettato da run_curve ma non arrivava fin qui).
    """
    rounds = rounds or d
    circuit = stim.Circuit.generated(
        f'surface_code:rotated_memory_{basis}',
        distance=d, rounds=rounds,
        after_clifford_depolarization=p,
        after_reset_flip_probability=p,
        before_measure_flip_probability=p,
    )
    sampler = circuit.compile_detector_sampler(seed=seed)
    dem = circuit.detector_error_model(decompose_errors=True)
    matching = pymatching.Matching.from_detector_error_model(dem)

    # Campionamento a blocchi: a d=9 il circuito ha ~720 detector, e chiedere
    # decine di milioni di shot in un colpo solo alloca decine di GiB. Il conteggio
    # dei fallimenti e' additivo, quindi si accumula blocco per blocco.
    BLOCCO = 500_000
    fails, fatti = 0, 0
    while fatti < shots:
        n = min(BLOCCO, shots - fatti)
        det, obs = sampler.sample(n, separate_observables=True)
        pred = matching.decode_batch(det)
        fails += int((pred != obs).any(axis=1).sum())
        fatti += n

    pL = fails / shots
    se = (pL * (1 - pL) / shots) ** 0.5
    return pL, se


def logical_error_rate_adattivo(d, p, basis, seed, target_fallimenti=200,
                                shots_min=200_000, shots_max=40_000_000):
    """p_L con numero di shot scelto per ottenere ~target_fallimenti eventi logici.

    Serve per le distanze grandi: a d=9 e p=2e-3 il tasso logico e' ~1e-5, e con
    200k shot si osservano 2 fallimenti — incertezza relativa del 70%, inutilizzabile
    per stimare una legge di scala. Il campionamento procede in due passate: la prima
    a shots_min stima l'ordine di grandezza di p_L, la seconda dimensiona il campione
    di conseguenza. Restituisce anche il numero di shot effettivamente usati, che va
    riportato perche' varia da punto a punto.
    """
    pL, se = logical_error_rate(d, p, shots_min, basis=basis, seed=seed)
    if pL * shots_min >= target_fallimenti:
        return pL, se, shots_min

    stima = max(pL, 1.0 / shots_min)          # se 0 fallimenti, limite superiore
    shots = int(min(shots_max, max(shots_min, target_fallimenti / stima)))
    pL, se = logical_error_rate(d, p, shots, basis=basis, seed=seed)
    return pL, se, shots


def run_curve(distances, p_list, shots, basis, seed=42):
    print(f"\n=== SURFACE CODE — p vs p_L (rotated_memory_{basis}, {shots} shot/punto) ===")
    header = "p".ljust(10) + "".join(f"d={d}".ljust(20) for d in distances)
    print(header)
    table = {d: [] for d in distances}
    for i, p in enumerate(p_list):
        row = f"{p:<10g}"
        for d in distances:
            # seed deterministico per (punto, distanza): l'esperimento e' rigenerabile
            if shots is None:
                pL, se, n = logical_error_rate_adattivo(d, p, basis, seed + i * 10 + d)
            else:
                pL, se = logical_error_rate(d, p, shots, basis=basis, rounds=d,
                                            seed=seed + i * 10 + d)
                n = shots
            table[d].append({'p': p, 'p_L': pL, 'p_L_se': se, 'shots': n})
            row += f"{f'{pL:.2e}±{se:.1e}':<20}"
        print(row)

    # --- flag 1: sanity a p piccolo (d maggiore => p_L minore) ---
    p0 = p_list[0]
    pL_small = [table[d][0]['p_L'] for d in distances]
    sanity = all(pL_small[i] >= pL_small[i + 1] for i in range(len(distances) - 1))
    print(f"\nSanity a p={p0}: p_L = "
          + " > ".join(f"{v:.4f}" for v in pL_small)
          + f"  → {'VERDE (d↑ ⇒ p_L↓)' if sanity else 'ROSSO'}")

    # --- flag decisivo: incrocio d_min vs d_max (soglia) ---
    d_lo, d_hi = distances[0], distances[-1]
    lo = np.array([r['p_L'] for r in table[d_lo]])
    hi = np.array([r['p_L'] for r in table[d_hi]])
    below = hi < lo                      # sotto soglia: d grande è meglio
    crossed = below.any() and (~below).any()
    p_th = None
    if crossed:
        i = np.where(np.diff(below.astype(int)) != 0)[0][0]
        p_th = 0.5 * (p_list[i] + p_list[i + 1])
    print(f"FLAG DECISIVO (incrocio d={d_lo}/d={d_hi}): "
          f"{'VERDE — soglia p_th ≈ ' + f'{p_th:.4f}' if crossed else 'ROSSO — nessun incrocio'}")
    return {'basis': basis, 'shots': shots, 'rounds': 'd',
            'table': {str(d): table[d] for d in distances},
            'sanity_ok': bool(sanity), 'threshold': p_th}


def main():
    ap = argparse.ArgumentParser(description="M7 — surface code (Stim + PyMatching)")
    ap.add_argument('--basis', choices=['x', 'z'], default='z')
    ap.add_argument('--shots', type=int, default=200000,
                    help='numero fisso di shot per punto; usare --adattivo per '
                         'dimensionarlo su ~200 fallimenti logici (serve a d>=9)')
    ap.add_argument('--adattivo', action='store_true',
                    help='ignora --shots e dimensiona il campione punto per punto')
    ap.add_argument('--distances', type=int, nargs='+', default=[3, 5, 7])
    ap.add_argument('--seed', type=int, default=42)
    args = ap.parse_args()

    p_list = [0.002, 0.003, 0.004, 0.005, 0.006, 0.008, 0.010]
    out = {'milestone': 'M7_surface', 'timestamp': datetime.now().isoformat(),
           'seed': args.seed}
    out['curve'] = run_curve(args.distances, p_list,
                             None if args.adattivo else args.shots,
                             args.basis, seed=args.seed)

    fname = f"results_M7_surface_{args.basis}_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(fname, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nRisultati salvati in: {fname}")


if __name__ == '__main__':
    main()
