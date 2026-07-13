"""
qec_coherent.py — Analisi complementare (Cap. 12): errore coerente vs errore di Pauli.
Motivazione: il paper su Plaquette (QC Design, arXiv 2026) mostra che i simulatori
Clifford-Pauli (come Stim, usato in M7) SOTTOSTIMANO l'errore logico quando il rumore
reale non è Pauli casuale — in particolare per errori COERENTI (sovrarotazioni da
calibrazione) e per il leakage. Qui si dimostra il meccanismo di base su scala trattabile.

Esperimento: un qubit, N operazioni "rumorose" ripetute, a parità di probabilità di errore
per operazione p:
  - modello di PAULI:    dopo ogni op, errore X con probabilità p  (accumulo stocastico)
  - errore COERENTE:     dopo ogni op, sovrarotazione RX(theta) con sin^2(theta/2)=p
                         (accumulo in ampiezza: gli angoli si sommano coerentemente)

Atteso: l'errore coerente cresce ~ (N*theta)^2 (quadratico), quello di Pauli ~ N*p (lineare):
il modello Pauli è quindi OTTIMISTICO. Confronto simulazione (Qiskit Aer) vs formula analitica.

Uso: python qec_coherent.py
"""
import argparse
import json
import os
from datetime import datetime

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, pauli_error


def sim_coherent(theta, N, shots, seed):
    qc = QuantumCircuit(1, 1)
    for _ in range(N):
        qc.rx(theta, 0)
    qc.measure(0, 0)
    sim = AerSimulator()
    c = sim.run(transpile(qc, sim), shots=shots, seed_simulator=seed).result().get_counts()
    return c.get('1', 0) / shots


def sim_pauli(p, N, shots, seed):
    nm = NoiseModel()
    nm.add_quantum_error(pauli_error([('X', p), ('I', 1 - p)]), ['id'], [0])
    qc = QuantumCircuit(1, 1)
    for _ in range(N):
        qc.id(0)
    qc.measure(0, 0)
    sim = AerSimulator(noise_model=nm)
    c = sim.run(transpile(qc, sim, optimization_level=0),
                shots=shots, seed_simulator=seed).result().get_counts()
    return c.get('1', 0) / shots


def main():
    ap = argparse.ArgumentParser(description="Errore coerente vs Pauli (accumulo)")
    ap.add_argument('--p', type=float, default=0.01, help="prob. di errore per operazione")
    ap.add_argument('--Nmax', type=int, default=20)
    ap.add_argument('--shots', type=int, default=20000)
    ap.add_argument('--seed', type=int, default=42)
    args = ap.parse_args()

    theta = 2 * np.arcsin(np.sqrt(args.p))     # sin^2(theta/2) = p
    Ns = list(range(1, args.Nmax + 1))
    print(f"=== ERRORE COERENTE vs PAULI (p={args.p} per operazione, theta={theta:.4f}) ===")
    print(f"{'N':<5}{'coerente (sim)':<18}{'coerente (teoria)':<20}"
          f"{'Pauli (sim)':<15}{'Pauli (teoria)':<16}{'rapporto coe/Pauli'}")
    pts = []
    for N in Ns:
        coe_sim = sim_coherent(theta, N, args.shots, args.seed)
        pau_sim = sim_pauli(args.p, N, args.shots, args.seed)
        coe_th = np.sin(N * theta / 2) ** 2
        pau_th = (1 - (1 - 2 * args.p) ** N) / 2
        ratio = coe_sim / pau_sim if pau_sim > 0 else float('nan')
        print(f"{N:<5}{coe_sim:<18.4f}{coe_th:<20.4f}{pau_sim:<15.4f}{pau_th:<16.4f}{ratio:.2f}")
        pts.append({'N': N, 'coherent_sim': coe_sim, 'coherent_theory': coe_th,
                    'pauli_sim': pau_sim, 'pauli_theory': pau_th})

    out = {'analysis': 'coherent_vs_pauli', 'p': args.p, 'theta': theta,
           'shots': args.shots, 'timestamp': datetime.now().isoformat(), 'points': pts}
    fname = f"results_coherent_vs_pauli_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(fname, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nMessaggio: a N moderati l'errore coerente supera di molto quello di Pauli "
          f"→ il modello Pauli è ottimistico.\nRisultati salvati in: {fname}")


if __name__ == '__main__':
    main()
