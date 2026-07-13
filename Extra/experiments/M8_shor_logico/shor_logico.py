"""
shor_logico.py — Milestone M8 (documento di indirizzo, §11): lo Shor logico.
Chiude l'arco della tesi con l'integrazione A LIVELLI: unisce Shor (M1-M4) e la correzione
d'errore (M5-M7) tramite l'errore logico p_L, senza codificare esplicitamente ogni qubit
(intrattabile). Si inietta un errore logico equivalente p_L dopo ogni gate del circuito di
Shor e si misura la probabilità di successo.

Metrica (§6 del documento): P_success = frazione di misure che producono i fattori corretti.
Si usa la probabilità PER SINGOLA MISURA (un grande run per punto), che è monotòna in p_L ed
evita l'artefatto della ricerca multi-candidato TOP-4 su N=15 (period finding r=4 degenere:
troppi esiti portano ai fattori, la P_success con TOP-4 non decresce -> curva non monotòna).

Istanza: N=15 (a=7, r=4). N=21/35 sono documentati come intrattabili da simulare (circuito
Beauregard: profondità ~9500 dopo transpilazione) -> barriera di scalabilità (§11.4).

Domanda del documento: quale p_L per P_success sopra soglia? La figura conclusiva (script
gen_shor_logico.py) confronta i regimi: Shor fisico nudo vs Steane vs surface code.

Uso (WSL, quantum-env):
    python shor_logico.py                 # N=15, curva P_success vs p_L (per-misura)
"""
import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'campagne_classiche_M1-M4'))
from shor_core import shor_circuit, extract_factors           # noqa: E402
from qiskit import transpile                                  # noqa: E402
from qiskit_aer import AerSimulator                           # noqa: E402
from qiskit_aer.noise import NoiseModel, depolarizing_error   # noqa: E402


def logical_noise(p_L):
    """Errore logico equivalente: depolarizing p_L su OGNI gate logico (1q e 2q)."""
    nm = NoiseModel()
    nm.add_all_qubit_quantum_error(depolarizing_error(p_L, 1), ['h', 'x', 'rz'])
    nm.add_all_qubit_quantum_error(depolarizing_error(p_L, 2), ['cx', 'swap', 'cp'])
    return nm


def p_success(N, a, n_count, p_L, shots, seed):
    """P_success per singola misura: frazione di shot che portano ai fattori corretti."""
    if p_L <= 0:
        sim = AerSimulator(method='matrix_product_state')
    else:
        sim = AerSimulator(noise_model=logical_noise(p_L), method='matrix_product_state')
    tqc = transpile(shor_circuit(N, a, n_count), sim, optimization_level=2)
    counts = sim.run(tqc, shots=shots, seed_simulator=seed).result().get_counts()
    total = sum(counts.values())
    good = sum(n for s, n in counts.items()
               if extract_factors(int(s, 2), n_count, N, a)[0] is not None)
    pS = good / total
    se = (pS * (1 - pS) / total) ** 0.5
    return pS, se


def run_curve(N, a, n_count, p_list, shots, seed):
    print(f"\n=== SHOR LOGICO — P_success vs p_L (N={N}, a={a}, per-misura, "
          f"{shots} shot/punto) ===")
    print(f"{'p_L':<10}{'P_success':<22}")
    pts = []
    for p_L in p_list:
        pS, se = p_success(N, a, n_count, p_L, shots, seed)
        print(f"{p_L:<10g}{f'{pS:.4f} +/- {se:.4f}':<22}")
        pts.append({'p_L': p_L, 'P_success': pS, 'P_success_se': se})
    # controllo monotonìa
    mono = all(pts[i]['P_success'] >= pts[i + 1]['P_success'] - 3 * pts[i + 1]['P_success_se']
               for i in range(len(pts) - 1))
    p0, pinf = pts[0]['P_success'], pts[-1]['P_success']
    print(f"\nMonotonìa: {'VERDE' if mono else 'ROSSO'} "
          f"(P_success: {p0:.3f} a p_L=0 → {pinf:.3f} a p_L={pts[-1]['p_L']})")
    print(f"Limite intrinseco N={N} (p_L=0): {p0:.3f}  |  plateau casuale: {pinf:.3f}")
    return {'N': N, 'a': a, 'n_count': n_count, 'shots': shots, 'points': pts,
            'P_ideal': p0, 'P_floor': pinf, 'monotonic': bool(mono)}


def main():
    ap = argparse.ArgumentParser(description="M8 — Shor logico (metrica per-misura)")
    ap.add_argument('--N', type=int, default=15)
    ap.add_argument('--a', type=int, default=7)
    ap.add_argument('--n_count', type=int, default=8)
    ap.add_argument('--shots', type=int, default=16384)
    ap.add_argument('--seed', type=int, default=42)
    args = ap.parse_args()

    p_list = [0.0, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50]
    out = {'milestone': 'M8_shor_logico', 'timestamp': datetime.now().isoformat(),
           'seed': args.seed}
    out['curve'] = run_curve(args.N, args.a, args.n_count, p_list, args.shots, args.seed)

    fname = f"results_M8_shor_logico_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(fname, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nRisultati salvati in: {fname}")


if __name__ == '__main__':
    main()
