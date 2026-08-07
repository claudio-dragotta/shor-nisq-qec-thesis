"""
topk_logico.py — M13: la ricerca multi-candidato TOP-K funziona anche a livello LOGICO?

PERCHE'. Il Cap. 14 propone come estensione "diretta e a basso costo" l'applicazione del
TOP-K allo Shor logico: li' la ricerca non dovrebbe piu' compensare il rumore fisico dei gate
(compito del codice correttore) ma l'errore logico residuo p_L. L'intestazione di
shor_logico.py afferma pero' che il TOP-4 su N=15 produce una curva NON monotona, a causa
della degenerazione del periodo (r=4: troppi esiti portano comunque ai fattori). Le due
affermazioni sono in tensione: questo script la scioglie con una misura.

DISEGNO. Per ciascun p_L si confrontano due metriche sullo stesso modello di rumore logico:
  per-misura : frazione di shot che producono i fattori (quella adottata in M8)
  TOP-K      : frazione di ITERAZIONI in cui almeno uno dei K esiti piu' frequenti li produce

Se la curva TOP-K resta piatta al crescere di p_L, la strategia non discrimina, e proporla
come estensione promettente su questa istanza sarebbe fuorviante.

Uso: ~/quantum-env/bin/python topk_logico.py
"""
import argparse
import json
from datetime import datetime

import numpy as np
from qiskit import transpile
from qiskit_aer import AerSimulator

from shor_logico import logical_noise
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'campagne_classiche_M1-M4'))
from shor_core import shor_circuit, extract_factors      # noqa: E402

N, A, N_COUNT = 15, 7, 8


def una_iterazione(tqc, sim, shots, seed, K):
    """Restituisce (successo_per_misura_frazione, successo_topk_booleano)."""
    counts = sim.run(tqc, shots=shots, seed_simulator=seed).result().get_counts()
    tot = sum(counts.values())
    buoni = sum(n for s, n in counts.items()
                if extract_factors(int(s, 2), N_COUNT, N, A)[0] is not None)
    ordinati = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:K]
    topk = any(extract_factors(int(s, 2), N_COUNT, N, A)[0] is not None
               for s, _ in ordinati)
    return buoni / tot, topk


def curva(p_list, iters, shots, K, seed):
    print(f"  {'p_L':<9}{'per-misura':<16}{'TOP-' + str(K):<16}{'TOP-1':<12}")
    print("  " + "-" * 52)
    out = []
    for p_L in p_list:
        sim = (AerSimulator(method='matrix_product_state') if p_L <= 0 else
               AerSimulator(noise_model=logical_noise(p_L),
                            method='matrix_product_state'))
        tqc = transpile(shor_circuit(N, A, N_COUNT), sim, optimization_level=2)
        pm, tk, t1 = [], [], []
        for r in range(iters):
            frac, ok = una_iterazione(tqc, sim, shots, seed * 1000 + r, K)
            _, ok1 = una_iterazione(tqc, sim, shots, seed * 1000 + r, 1)
            pm.append(frac); tk.append(ok); t1.append(ok1)
        row = {'p_L': p_L, 'per_misura': float(np.mean(pm)),
               'topk': float(np.mean(tk)), 'top1': float(np.mean(t1)),
               'iters': iters, 'shots': shots}
        out.append(row)
        print(f"  {p_L:<9g}{row['per_misura']:<16.4f}{row['topk']:<16.4f}"
              f"{row['top1']:<12.4f}", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser(description='M13 — TOP-K a livello logico')
    ap.add_argument('--iters', type=int, default=40)
    ap.add_argument('--shots', type=int, default=1024)
    ap.add_argument('--K', type=int, default=4)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--p-list', type=float, nargs='+',
                    default=[0.0, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2])
    args = ap.parse_args()

    print('=' * 60)
    print(f"M13 — TOP-{args.K} a livello logico (N={N}, a={A})")
    print(f"    {args.iters} iterazioni x {args.shots} shot per punto")
    print('=' * 60)
    pts = curva(args.p_list, args.iters, args.shots, args.K, args.seed)

    pm = np.array([r['per_misura'] for r in pts])
    tk = np.array([r['topk'] for r in pts])
    esc_pm = pm[0] - pm[-1]
    esc_tk = tk[0] - tk[-1]
    mono_tk = all(tk[i] >= tk[i + 1] - 1e-9 for i in range(len(tk) - 1))

    print('\n' + '=' * 60)
    print('ESITO M13')
    print('=' * 60)
    print(f"  escursione per-misura (p_L=0 -> max) : {esc_pm:.4f}")
    print(f"  escursione TOP-{args.K}                    : {esc_tk:.4f}")
    print(f"  la curva TOP-{args.K} e' monotona decrescente: {'si' if mono_tk else 'NO'}")
    if esc_tk < 0.1:
        flag = (f"TOP-{args.K} NON discrimina a livello logico su N=15: la curva resta "
                f"sostanzialmente piatta (escursione {esc_tk:.3f}). Confermata la nota di "
                f"shor_logico.py; proporlo come estensione promettente su questa istanza "
                f"sarebbe fuorviante.")
    else:
        flag = (f"TOP-{args.K} discrimina anche a livello logico (escursione {esc_tk:.3f}): "
                f"la proposta del Cap. 14 e' sostenibile.")
    print(f"\n  {flag}")

    fn = f"results_M13_topk_logico_{datetime.now():%Y%m%d_%H%M%S}.json"
    json.dump({'milestone': 'M13_topk_logico', 'timestamp': datetime.now().isoformat(),
               'N': N, 'a': A, 'K': args.K, 'iters': args.iters, 'shots': args.shots,
               'escursione_per_misura': float(esc_pm), 'escursione_topk': float(esc_tk),
               'topk_monotona': bool(mono_tk), 'flag': flag, 'punti': pts},
              open(fn, 'w'), indent=2)
    print(f"\nRisultati salvati in: {fn}")


if __name__ == '__main__':
    main()
