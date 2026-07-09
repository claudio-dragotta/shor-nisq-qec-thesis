"""
qec_steane.py — Milestone M6 (documento di indirizzo, §9): codice di Steane [[7,1,3]].
Codice CENTRALE della tesi: primo codice che corregge un errore ARBITRARIO (X, Z o Y)
su un singolo qubit.

Costruito per gradi, con validazione a flag (piano_azione_qec.md, Parte V):
  --mode check   : prepara |0_L> e misura i 6 stabilizzatori -> DEVE dare 000000
                   (lo stato e' nel code space). Se no, l'encoding e' sbagliato: STOP.
  --mode verify  : inietta X, Z, Y su ciascuno dei 7 qubit -> la syndrome table deve
                   essere BIIETTIVA (7 sindromi distinte e non nulle) e Y deve accendere
                   ENTRAMBE le sindromi. Flag decisivo di M6.

Convenzione stabilizzatori (documento §9.2), qubit 0..6 da sinistra a destra:
  X-type (rilevano errori Z):  gx1=X{3,4,5,6}  gx2=X{1,2,5,6}  gx3=X{0,2,4,6}
  Z-type (rilevano errori X):  gz1=Z{3,4,5,6}  gz2=Z{1,2,5,6}  gz3=Z{0,2,4,6}
La sindrome Z di un errore X sul qubit i e' la colonna i della matrice di Hamming
(biiezione qubit <-> sindrome). Idem, per dualita' CSS, la sindrome X di un errore Z.

Uso (WSL, quantum-env attivo):
    python qec_steane.py --mode check
    python qec_steane.py --mode verify
"""
import argparse
import json
from datetime import datetime

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit_aer import AerSimulator

DATA = list(range(7))              # qubit dati 0..6
# supporti degli stabilizzatori (0-indexed)
GZ = [[3, 4, 5, 6], [1, 2, 5, 6], [0, 2, 4, 6]]   # Z-type: rilevano X
GX = [[3, 4, 5, 6], [1, 2, 5, 6], [0, 2, 4, 6]]   # X-type: rilevano Z
# ancilla: 7,8,9 per gz1,gz2,gz3 ; 10,11,12 per gx1,gx2,gx3
ANC_Z = [7, 8, 9]
ANC_X = [10, 11, 12]
# seed dell'encoding: qubit presenti in UN solo X-stabilizzatore
SEED = {3: GX[0], 1: GX[1], 0: GX[2]}   # seed -> supporto da propagare


def encode_zero_L(qc):
    """Prepara |0_L> = sovrapposizione uniforme degli 8 codeword."""
    for s in SEED:                      # H sui 3 seed
        qc.h(s)
    for s, support in SEED.items():     # propaga con CNOT il seed sul resto del supporto
        for d in support:
            if d != s:
                qc.cx(s, d)


def measure_syndrome(qc):
    """Estrae le 6 sindromi con ancilla dedicate; misura su 6 bit classici."""
    # Z-type (rilevano X): parita' Z dei data -> ancilla
    for k, support in enumerate(GZ):
        for d in support:
            qc.cx(d, ANC_Z[k])
    # X-type (rilevano Z): ancilla in |+>, CNOT ancilla->data, H, misura
    for k, support in enumerate(GX):
        qc.h(ANC_X[k])
        for d in support:
            qc.cx(ANC_X[k], d)
        qc.h(ANC_X[k])
    for k in range(3):
        qc.measure(ANC_Z[k], k)         # c0,c1,c2 = sindrome Z (gz1,gz2,gz3)
    for k in range(3):
        qc.measure(ANC_X[k], 3 + k)     # c3,c4,c5 = sindrome X (gx1,gx2,gx3)


def build(inject=None):
    """inject = None | ('X'|'Y'|'Z', qubit)."""
    qr = QuantumRegister(13, 'q')
    cr = ClassicalRegister(6, 'c')
    qc = QuantumCircuit(qr, cr)
    encode_zero_L(qc)
    qc.barrier()
    if inject is not None:
        p, i = inject
        getattr(qc, p.lower())(i)       # qc.x/qc.y/qc.z sul qubit i
    qc.barrier()
    measure_syndrome(qc)
    return qc


def _parse(bitstring):
    """Ritorna (sindrome_Z, sindrome_X) come tuple di 3 bit. Stringa Qiskit = c5..c0."""
    b = bitstring.replace(' ', '')[::-1]        # -> c0 c1 c2 c3 c4 c5
    sz = (int(b[0]), int(b[1]), int(b[2]))
    sx = (int(b[3]), int(b[4]), int(b[5]))
    return sz, sx


def run_check(shots=2000, seed=42):
    """Flag: |0_L> deve dare sindrome 000000 su tutti gli shot."""
    sim = AerSimulator()
    qc = build(inject=None)
    tqc = transpile(qc, sim, optimization_level=0)
    counts = sim.run(tqc, shots=shots, seed_simulator=seed).result().get_counts()
    print("\n=== CHECK ENCODING — |0_L> nel code space ===")
    all_zero = list(counts.keys()) == ['000000']
    for bitstring, n in sorted(counts.items(), key=lambda x: -x[1]):
        sz, sx = _parse(bitstring)
        print(f"  sindrome (Z={sz}, X={sx})  x{n}")
    flag = "VERDE" if all_zero else "ROSSO"
    print(f"FLAG encoding: {flag} "
          f"({'tutti gli shot danno 000000' if all_zero else 'sindrome non nulla → encoding/misura da rivedere'})")
    return {'all_zero': all_zero, 'counts': counts}


def run_verify(seed=42):
    """Flag decisivo: syndrome table biiettiva per X, Z; Y accende entrambe."""
    sim = AerSimulator()
    print("\n=== VERIFY — syndrome table (iniezione su ciascun qubit) ===")
    tables = {}
    for pauli in ['X', 'Z', 'Y']:
        rows = []
        seen = {}
        print(f"\n-- errori {pauli} --")
        print(f"{'qubit':<8}{'sindrome Z':<16}{'sindrome X':<16}{'nota'}")
        for i in DATA:
            qc = build(inject=(pauli, i))
            tqc = transpile(qc, sim, optimization_level=0)
            counts = sim.run(tqc, shots=1, seed_simulator=seed + i).result().get_counts()
            sz, sx = _parse(next(iter(counts)))
            note = ''
            if pauli == 'X':
                note = 'Z=0 atteso' if sx == (0, 0, 0) else 'X-synd inatteso!'
                key = sz
            elif pauli == 'Z':
                note = 'X=0 atteso' if sz == (0, 0, 0) else 'Z-synd inatteso!'
                key = sx
            else:
                note = 'entrambe' if sz != (0, 0, 0) and sx != (0, 0, 0) else 'Y non doppio!'
                key = (sz, sx)
            seen.setdefault(key, []).append(i)
            print(f"q{i:<7}{str(sz):<16}{str(sx):<16}{note}")
            rows.append({'qubit': i, 'sz': sz, 'sx': sx})
        # biiettivita': 7 chiavi distinte, nessuna nulla per X/Z
        distinct = len(seen) == 7
        nonzero = all(k != (0, 0, 0) for k in seen) if pauli in ('X', 'Z') else True
        ok = distinct and nonzero
        print(f"FLAG {pauli}: {'VERDE' if ok else 'ROSSO'} "
              f"({'7 sindromi distinte' if distinct else 'COLLISIONE sindromi'}"
              f"{'' if nonzero else ', sindrome nulla presente'})")
        tables[pauli] = {'rows': rows, 'bijective': ok}
    all_ok = all(t['bijective'] for t in tables.values())
    print(f"\nFLAG DECISIVO M6: {'VERDE — syndrome table biiettiva' if all_ok else 'ROSSO'}")
    return tables


def run_curve(p_list, shots=100000, seed=42):
    """
    Logical error rate p_L sotto rumore depolarizing p per qubit, via Monte Carlo
    Pauli-frame (metodo standard, cattura errori X_L e Z_L). Correzione a peso minimo
    dalla syndrome table di Hamming (già verificata biiettiva in --mode verify).
    Flag: p_L ∝ p² (pendenza log-log ≈ 2) e pseudo-soglia dove p_L < p.
    """
    rng = np.random.default_rng(seed)
    idx = np.arange(shots)
    print(f"\n=== CURVA p vs p_L — Steane [[7,1,3]] (depolarizing, {shots} shot/punto) ===")
    print(f"{'p':<8}{'p_L':<22}{'p_L/p^2':<12}{'p_L<p?':<8}{'riga LaTeX'}")
    results = []
    for p in p_list:
        r = rng.random((shots, 7))
        ex = np.zeros((shots, 7), dtype=np.int8)   # parte X dell'errore
        ez = np.zeros((shots, 7), dtype=np.int8)   # parte Z dell'errore
        # I: r<1-p ; X: [1-p,1-2p/3) ; Y: [1-2p/3,1-p/3) ; Z: [1-p/3,1)
        X_reg = (r >= 1 - p) & (r < 1 - 2 * p / 3)
        Y_reg = (r >= 1 - 2 * p / 3) & (r < 1 - p / 3)
        Z_reg = (r >= 1 - p / 3)
        ex[X_reg | Y_reg] = 1
        ez[Y_reg | Z_reg] = 1
        # sindrome Z (rileva parte X) -> correzione X a peso minimo
        sz = (ex[:, GZ[0]].sum(1) % 2) * 4 + (ex[:, GZ[1]].sum(1) % 2) * 2 + (ex[:, GZ[2]].sum(1) % 2)
        m = sz > 0
        ex[idx[m], sz[m] - 1] ^= 1
        # sindrome X (rileva parte Z) -> correzione Z a peso minimo
        sx = (ez[:, GX[0]].sum(1) % 2) * 4 + (ez[:, GX[1]].sum(1) % 2) * 2 + (ez[:, GX[2]].sum(1) % 2)
        m = sx > 0
        ez[idx[m], sx[m] - 1] ^= 1
        # errore logico: residuo con componente logica (X_L=X^7, Z_L=Z^7 -> parità dispari)
        fail = ((ex.sum(1) % 2) | (ez.sum(1) % 2)).mean()
        se = (fail * (1 - fail) / shots) ** 0.5
        ratio = fail / p**2 if p > 0 else 0.0
        latex = f"${p:g}$ & ${fail:.5f} \\pm {se:.5f}$ \\\\"
        print(f"{p:<8g}{f'{fail:.5f} +/- {se:.5f}':<22}{ratio:<12.2f}{'sì' if fail < p else 'no':<8}{latex}")
        results.append({'p': p, 'p_L': float(fail), 'p_L_se': float(se), 'ratio_p2': float(ratio)})
    # stima pendenza log-log tra i due p più piccoli non nulli
    small = [r for r in results if r['p'] > 0 and r['p_L'] > 0][:2]
    if len(small) == 2:
        slope = (np.log(small[1]['p_L']) - np.log(small[0]['p_L'])) / \
                (np.log(small[1]['p']) - np.log(small[0]['p']))
        print(f"\nPendenza log-log a p piccolo: {slope:.2f} "
              f"(FLAG {'VERDE' if 1.7 < slope < 2.3 else 'ROSSO'} — atteso ≈2 per codice d=3)")
    return {'shots': shots, 'points': results}


def main():
    ap = argparse.ArgumentParser(description="M6 — codice di Steane [[7,1,3]]")
    ap.add_argument('--mode', choices=['check', 'verify', 'curve', 'both'], default='both')
    ap.add_argument('--shots', type=int, default=100000)
    ap.add_argument('--seed', type=int, default=42)
    args = ap.parse_args()

    out = {'milestone': 'M6_steane', 'timestamp': datetime.now().isoformat(), 'seed': args.seed}
    if args.mode in ('check', 'both'):
        out['check'] = run_check(seed=args.seed)
    if args.mode in ('verify', 'both'):
        out['verify'] = {k: v['bijective'] for k, v in run_verify(seed=args.seed).items()}
    if args.mode == 'curve':
        p_list = [0.005, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30]
        out['curve'] = run_curve(p_list, shots=args.shots, seed=args.seed)

    fname = f"results_M6_steane_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(fname, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nRisultati salvati in: {fname}")


if __name__ == '__main__':
    main()
