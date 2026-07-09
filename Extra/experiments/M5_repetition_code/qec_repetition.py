"""
qec_repetition.py — Milestone M5 (documento di indirizzo, §7 e Tab. 6).
Primo laboratorio di correzione d'errore: il codice a ripetizione a 3 qubit.

Due codici duali:
  - bit-flip  (basis='Z'): protegge |0_L>,|1_L> dagli errori X; stabilizzatori Z0Z1, Z1Z2.
  - phase-flip(basis='X'): protegge |+_L>,|-_L> dagli errori Z; stabilizzatori X0X1, X1X2.

Due esperimenti:
  --mode verify : iniezione DETERMINISTICA di un errore su ciascun qubit -> tabella
                  sindrome->qubit->correzione (senza rumore). Dimostra che la sindrome
                  identifica il qubit colpito.
  --mode curve  : curva Monte Carlo p (errore fisico) vs p_L (errore logico), con
                  confronto alla previsione analitica del voto di maggioranza 3p^2 - 2p^3.

Riusa i pattern di shor_core.py: seed espliciti, output JSON con timestamp, righe LaTeX
pronte per la tabella [DA COMPLETARE] del Cap. 11 (subsec:risultati_repetition).

Uso (in WSL, con quantum-env attivo):
    python qec_repetition.py --mode verify
    python qec_repetition.py --mode curve --shots 20000
    python qec_repetition.py --mode both --basis Z
"""
import argparse
import json
from datetime import datetime

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, pauli_error


DATA = [0, 1, 2]          # qubit dati
ANC = [3, 4]              # qubit ancilla (misura di sindrome)
# Lookup sindrome (a0, a1) -> qubit dato da correggere. a0 copre {0,1}, a1 copre {1,2}.
SYNDROME_LOOKUP = {(0, 0): None, (1, 0): 0, (1, 1): 1, (0, 1): 2}


def build_circuit(logical_value, basis, inject=None):
    """
    Costruisce il circuito del codice a ripetizione.
      logical_value : 0 o 1 (stato logico da proteggere)
      basis         : 'Z' (bit-flip) o 'X' (phase-flip)
      inject        : None, oppure il qubit dato (0/1/2) su cui iniettare un errore
                      deterministico (X per basis Z, Z per basis X) — usato in verify.
    L'iniezione stocastica di rumore in 'curve' è gestita fuori, via noise model su 'id'.
    """
    qr = QuantumRegister(5, 'q')
    cr = ClassicalRegister(5, 'c')   # c0,c1 = sindrome; c2,c3,c4 = data
    qc = QuantumCircuit(qr, cr)

    # --- Codifica ---
    if logical_value == 1:
        qc.x(0)
    qc.cx(0, 1)
    qc.cx(0, 2)
    if basis == 'X':
        qc.h(DATA)          # |+_L> = H^3 |0_L>
    qc.barrier()

    # --- Iniezione deterministica dell'errore (solo verify) ---
    if inject is not None:
        if basis == 'Z':
            qc.x(inject)    # errore X, rilevato dagli stabilizzatori Z
        else:
            qc.z(inject)    # errore Z, rilevato dagli stabilizzatori X
    else:
        # Punto di iniezione del rumore stocastico: identita' "rumorose" sui data.
        for q in DATA:
            qc.id(q)
    qc.barrier()

    # --- Estrazione della sindrome ---
    if basis == 'Z':
        # stabilizzatori Z0Z1 (ancilla 3) e Z1Z2 (ancilla 4)
        qc.cx(0, 3); qc.cx(1, 3)
        qc.cx(1, 4); qc.cx(2, 4)
    else:
        # stabilizzatori X0X1 (ancilla 3) e X1X2 (ancilla 4)
        qc.h(3); qc.cx(3, 0); qc.cx(3, 1); qc.h(3)
        qc.h(4); qc.cx(4, 1); qc.cx(4, 2); qc.h(4)
    qc.measure(ANC[0], 0)
    qc.measure(ANC[1], 1)

    # --- Lettura dei data (in base X se phase-flip) ---
    if basis == 'X':
        qc.h(DATA)
    qc.measure(DATA[0], 2)
    qc.measure(DATA[1], 3)
    qc.measure(DATA[2], 4)
    return qc


def _parse_bits(bitstring):
    """La stringa Qiskit e' c4 c3 c2 c1 c0; ritorna (a0, a1, [d0,d1,d2])."""
    b = bitstring.replace(' ', '')[::-1]     # -> c0 c1 c2 c3 c4
    a0, a1 = int(b[0]), int(b[1])
    data = [int(b[2]), int(b[3]), int(b[4])]
    return a0, a1, data


def _decode_logical(a0, a1, data):
    """Applica la correzione indicata dalla sindrome, poi vota a maggioranza."""
    corrected = data[:]
    q = SYNDROME_LOOKUP[(a0, a1)]
    if q is not None:
        corrected[q] ^= 1
    return 1 if sum(corrected) >= 2 else 0


# ---------------------------------------------------------------------------
def run_verify(basis, seed=42):
    """Tabella di verifica: iniezione X/Z su ciascun qubit -> sindrome osservata."""
    sim = AerSimulator()
    rows = []
    print(f"\n=== VERIFICA SINDROME — codice {'bit-flip' if basis=='Z' else 'phase-flip'} "
          f"(basis {basis}) ===")
    print(f"{'errore iniettato':<20}{'sindrome (a0,a1)':<20}{'qubit dedotto':<16}{'atteso':<10}{'esito'}")
    for inject in [None, 0, 1, 2]:
        qc = build_circuit(logical_value=0, basis=basis, inject=inject)
        tqc = transpile(qc, sim, optimization_level=0)
        counts = sim.run(tqc, shots=1, seed_simulator=seed).result().get_counts()
        bitstring = next(iter(counts))
        a0, a1, _ = _parse_bits(bitstring)
        deduced = SYNDROME_LOOKUP[(a0, a1)]
        label = 'nessuno' if inject is None else f"{'X' if basis=='Z' else 'Z'} su q{inject}"
        ok = (deduced == inject)
        print(f"{label:<20}{f'({a0},{a1})':<20}{str(deduced):<16}{str(inject):<10}"
              f"{'OK' if ok else 'ERRORE'}")
        rows.append({'inject': inject, 'syndrome': [a0, a1], 'deduced': deduced, 'ok': ok})
    all_ok = all(r['ok'] for r in rows)
    print(f"\nEsito complessivo: {'TUTTE CORRETTE' if all_ok else 'ci sono discrepanze'}")
    return {'basis': basis, 'rows': rows, 'all_ok': all_ok}


def run_curve(basis, p_list, shots=20000, seed=42):
    """Curva p (errore fisico per qubit) vs p_L (errore logico dopo correzione)."""
    err_pauli = 'X' if basis == 'Z' else 'Z'    # errore rilevato dal codice
    print(f"\n=== CURVA p vs p_L — codice {'bit-flip' if basis=='Z' else 'phase-flip'} "
          f"(basis {basis}, {shots} shot/punto) ===")
    print(f"{'p':<10}{'p_L Monte Carlo':<20}{'3p^2-2p^3 (teoria)':<22}{'riga LaTeX'}")
    results = []
    for p in p_list:
        nm = NoiseModel()
        err = pauli_error([(err_pauli, p), ('I', 1 - p)])
        for q in DATA:
            nm.add_quantum_error(err, ['id'], [q])
        sim = AerSimulator(noise_model=nm)
        qc = build_circuit(logical_value=0, basis=basis, inject=None)
        tqc = transpile(qc, sim, optimization_level=0)
        counts = sim.run(tqc, shots=shots, seed_simulator=seed).result().get_counts()

        fails = 0
        for bitstring, n in counts.items():
            a0, a1, data = _parse_bits(bitstring)
            if _decode_logical(a0, a1, data) != 0:    # logical atteso = 0
                fails += n
        p_l = fails / shots
        p_theory = 3 * p**2 - 2 * p**3
        se = (p_l * (1 - p_l) / shots) ** 0.5         # errore standard binomiale
        latex = f"${p:g}$ & ${p_l:.4f} \\pm {se:.4f}$ & ${p_theory:.4f}$ \\\\"
        print(f"{p:<10g}{f'{p_l:.4f} +/- {se:.4f}':<20}{p_theory:<22.4f}{latex}")
        results.append({'p': p, 'p_L': p_l, 'p_L_se': se, 'p_L_theory': p_theory})
    return {'basis': basis, 'shots': shots, 'points': results}


def main():
    ap = argparse.ArgumentParser(description="M5 — codice a ripetizione (QEC)")
    ap.add_argument('--mode', choices=['verify', 'curve', 'both'], default='both')
    ap.add_argument('--basis', choices=['Z', 'X'], default='Z',
                    help="Z = bit-flip (default), X = phase-flip")
    ap.add_argument('--shots', type=int, default=20000)
    ap.add_argument('--seed', type=int, default=42)
    args = ap.parse_args()

    p_list = [0.0, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50]
    out = {'milestone': 'M5_repetition', 'basis': args.basis,
           'timestamp': datetime.now().isoformat(), 'seed': args.seed}

    if args.mode in ('verify', 'both'):
        out['verify'] = run_verify(args.basis, seed=args.seed)
    if args.mode in ('curve', 'both'):
        out['curve'] = run_curve(args.basis, p_list, shots=args.shots, seed=args.seed)

    fname = f"results_M5_repetition_{args.basis}_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(fname, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nRisultati salvati in: {fname}")


if __name__ == '__main__':
    main()
