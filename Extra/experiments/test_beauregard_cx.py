"""
Misura il gate count CX dell'implementazione Beauregard per N=21.
Eseguire con: python test_beauregard_cx.py
"""
import numpy as np
from math import ceil, log2
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import QFT
from qiskit_aer import AerSimulator

sim = AerSimulator(method='statevector')


def phi_add(n, a, inverse=False):
    """Draper adder: aggiunge costante a al registro di n qubit in base di Fourier."""
    qc = QuantumCircuit(n, name=f'phiADD({a})' + ('†' if inverse else ''))
    sign = -1 if inverse else 1
    for j in range(n):
        angle = sign * 2 * np.pi * a / (2 ** (n - j))
        qc.p(angle, j)
    return qc


def qft_n(n, inverse=False):
    return QFT(n, do_swaps=False, inverse=inverse).decompose()


def cc_phi_add(n, a, inverse=False):
    """Doubly-controlled Draper adder (2 ctrl + n b-qubits)."""
    qc = QuantumCircuit(n + 2, name=f'ccphiADD({a})' + ('†' if inverse else ''))
    c1, c2 = 0, 1
    b = list(range(2, n + 2))
    sign = -1 if inverse else 1
    for j in range(n):
        angle = sign * 2 * np.pi * a / (2 ** (n - j))
        # C2P decomposition: CP(a/2, c1, b); CX(c1,c2); CP(-a/2, c2, b); CX(c1,c2); CP(a/2, c2, b)
        qc.cp(angle / 2, c1, b[j])
        qc.cx(c1, c2)
        qc.cp(-angle / 2, c2, b[j])
        qc.cx(c1, c2)
        qc.cp(angle / 2, c2, b[j])
    return qc


def c_phi_add(n, a, inverse=False):
    """Singly-controlled Draper adder (1 ctrl + n b-qubits)."""
    qc = QuantumCircuit(n + 1, name=f'cphiADD({a})' + ('†' if inverse else ''))
    ctrl = 0
    b = list(range(1, n + 1))
    sign = -1 if inverse else 1
    for j in range(n):
        angle = sign * 2 * np.pi * a / (2 ** (n - j))
        qc.cp(angle, ctrl, b[j])
    return qc


def phi_add_mod_N_gate(n_b, a, N):
    """
    Doubly-controlled phi_add mod N (Beauregard 2002, Fig.2).
    Qubits: ctrl1, ctrl2, b[0..n_b-1], ancilla  (total = n_b + 3)
    """
    total = n_b + 3
    qc = QuantumCircuit(total, name=f'phiADDmodN({a},{N})')
    c1, c2 = 0, 1
    b = list(range(2, 2 + n_b))
    anc = 2 + n_b

    # Step 1: cc_phi_add(a)
    qc.compose(cc_phi_add(n_b, a), [c1, c2] + b, inplace=True)
    # Step 2: phi_add(-N)
    qc.compose(phi_add(n_b, N, inverse=True), b, inplace=True)
    # Step 3: QFT†
    qc.compose(qft_n(n_b, inverse=True), b, inplace=True)
    # Step 4: CNOT(b[0], anc)  — b[0] is MSB (sign bit)
    qc.cx(b[0], anc)
    # Step 5: QFT
    qc.compose(qft_n(n_b), b, inplace=True)
    # Step 6: c_phi_add(N, ctrl=anc)
    qc.compose(c_phi_add(n_b, N), [anc] + b, inplace=True)
    # Step 7: cc_phi_add(-a)
    qc.compose(cc_phi_add(n_b, a, inverse=True), [c1, c2] + b, inplace=True)
    # Step 8: phi_add(N)
    qc.compose(phi_add(n_b, N), b, inplace=True)
    # Step 9: QFT†
    qc.compose(qft_n(n_b, inverse=True), b, inplace=True)
    # Step 10: X; CNOT(b[0], anc); X
    qc.x(b[0])
    qc.cx(b[0], anc)
    qc.x(b[0])
    # Step 11: QFT
    qc.compose(qft_n(n_b), b, inplace=True)
    # Step 12: phi_add(-N)
    qc.compose(phi_add(n_b, N, inverse=True), b, inplace=True)
    # Step 13: cc_phi_add(a)
    qc.compose(cc_phi_add(n_b, a), [c1, c2] + b, inplace=True)
    return qc


def c_mult_mod_N_gate(n, a, N):
    """
    Controlled modular multiplication: ctrl, x[n], b[n+1], anc
    |ctrl>|x>|0>|0> -> |ctrl>|x>|ax mod N>|0> (if ctrl=1)
    total qubits = 1 + n + (n+1) + 1 = 2n + 3
    """
    n_b = n + 1  # b register (1 extra bit for overflow)
    total = 1 + n + n_b + 1  # ctrl + x + b + anc
    qc = QuantumCircuit(total, name=f'cMULT({a},{N})')
    ctrl = 0
    x = list(range(1, n + 1))
    b = list(range(n + 1, n + 1 + n_b))
    anc = n + 1 + n_b

    # Apply QFT to b register
    qc.compose(qft_n(n_b), b, inplace=True)

    # For each bit of x: if ctrl=1 AND x[j]=1, add a*2^j mod N to b
    for j in range(n):
        a_shifted = (a * pow(2, j, N)) % N
        # doubly controlled on ctrl and x[j]
        qc.compose(phi_add_mod_N_gate(n_b, a_shifted, N),
                   [ctrl, x[j]] + b + [anc], inplace=True)

    # Apply QFT† to b
    qc.compose(qft_n(n_b, inverse=True), b, inplace=True)
    return qc


def beauregard_c_amod(a, N, power):
    """
    Controlled-U^power: |ctrl>|x> -> |ctrl>|a^power * x mod N>
    Using Beauregard: CMULT(a,N) + SWAP + CMULT(a_inv,N)†
    n = ceil(log2(N+1))
    total qubits = 1 + n + (n+1) + 1
    """
    n = ceil(log2(N + 1))
    n_b = n + 1
    a_pow = pow(a, power, N)
    a_inv = pow(a_pow, -1, N)  # modular inverse

    total = 1 + n + n_b + 1
    qc = QuantumCircuit(total, name=f'{a}^{power} mod {N} [B]')
    ctrl = 0
    x = list(range(1, n + 1))
    b = list(range(n + 1, n + 1 + n_b))
    anc = n + 1 + n_b

    # Phase 1: CMULT(a_pow) into b
    qc.compose(c_mult_mod_N_gate(n, a_pow, N), [ctrl] + x + b + [anc], inplace=True)

    # Phase 2: Controlled SWAP x <-> b[0..n-1]
    for i in range(n):
        qc.cswap(ctrl, x[i], b[i])

    # Phase 3: CMULT(a_inv)† to uncompute b
    qc.compose(c_mult_mod_N_gate(n, a_inv, N).inverse(),
               [ctrl] + x + b + [anc], inplace=True)

    return qc


# ---- Misura gate count ----
print('=== Beauregard gate count per N=21, a=2, n_count=8 ===\n')
N, a = 21, 2
n = ceil(log2(N + 1))
print(f'N={N}, a={a}, n_work={n}, n_b={n+1}')

total_cx = 0
seen = {}
for j in range(8):
    power = 2 ** j
    a_pow = pow(a, power, N)
    if a_pow in seen:
        cx = seen[a_pow]
        print(f'  j={j}  a^{power:4d} mod {N} = {a_pow:2d}  →  CX={cx} [cached]')
        total_cx += cx
        continue
    qc = beauregard_c_amod(a, N, power)
    t = transpile(qc, sim, optimization_level=2)
    ops = t.count_ops()
    cx = ops.get('cx', 0)
    seen[a_pow] = cx
    total_cx += cx
    print(f'  j={j}  a^{power:4d} mod {N} = {a_pow:2d}  →  CX={cx}')

print(f'\nTotale CX modular exp (n_count=8): {total_cx}')
# IQFT su 8 qubit
iqft_cx = 8 * 7 // 2
print(f'IQFT CX (n_count=8): {iqft_cx}')
grand_total = total_cx + iqft_cx
print(f'Grand total CX: {grand_total}')

print('\nP_survival in funzione di eps_2q:')
for eps in [0.01, 0.005, 0.002, 0.001, 0.0005, 0.0002]:
    p = (1 - eps) ** grand_total
    print(f'  eps={eps:.4f}  P_surv={p:.6f}')

print('\nCFR UnitaryGate N=21: CX≈10040, P_surv(eps=0.01)≈1e-44 (inutilizzabile)')
