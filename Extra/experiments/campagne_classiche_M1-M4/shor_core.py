"""
shor_core.py — Funzioni core per la tesi di Claudio Dragotta.
QPE per l'algoritmo di Shor: N=15 (c_amod15 textbook), N=21, N=35 (generale).
"""
import hashlib
import json
import platform
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version

import numpy as np
from math import gcd, ceil, log2
from fractions import Fraction
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import UnitaryGate
from qiskit_aer import AerSimulator
from qiskit_aer.noise import (
    NoiseModel, depolarizing_error, thermal_relaxation_error, ReadoutError
)
from beauregard import beauregard_c_amod


# Contratto sperimentale condiviso da training, baseline e sweep.  Il circuito
# viene sempre compilato nella stessa base nativa illustrativa: RZ e' virtuale,
# SX/X sono le operazioni fisiche 1Q e CX l'operazione fisica 2Q.
BASIS_GATES = ("rz", "sx", "x", "cx")
TRANSPILE_SEED = 20260819
CIRCUIT_REVISION = "shor-qpe-v2-amod15-correct"
NOISE_MODEL_REVISION = "uniform-rz-virtual-v2"
POSTPROCESS_REVISION = "seeded-sha256-tie-break-v1"
GATE_TIME_1Q_NS = 50.0
GATE_TIME_2Q_NS = 300.0


# --- Inverse QFT (textbook convention) ---
def inverse_qft(n_qubits):
    qc = QuantumCircuit(n_qubits, name='QFT†')
    for qubit in range(n_qubits // 2):
        qc.swap(qubit, n_qubits - qubit - 1)
    for j in range(n_qubits):
        for m in range(j):
            qc.cp(-np.pi / float(2 ** (j - m)), m, j)
        qc.h(j)
    return qc


# --- Controlled modular exponentiation (textbook loop-based, N=15 only) ---
def c_amod15(a, power):
    if a not in [2, 7, 8, 11, 13]:
        raise ValueError(f"a={a} non supportato per N=15.")
    U = QuantumCircuit(4)
    for _ in range(power):
        if a in [2, 13]:
            U.swap(0, 1); U.swap(1, 2); U.swap(2, 3)
        if a in [7, 8]:
            U.swap(2, 3); U.swap(1, 2); U.swap(0, 1)
        if a == 11:
            U.swap(1, 3); U.swap(0, 2)
        if a in [7, 11, 13]:
            U.x(range(4))
    U.name = f'{a}^{power} mod 15'
    # Esplicito per mantenere la decomposizione corrente anche con Qiskit 3.
    return U.control(annotated=False)


# --- Controlled modular exponentiation (generale, per N qualsiasi) ---
def c_amod(a, N, power):
    """
    Gate controllato U|x⟩ = |a^power·x mod N⟩ via matrice di permutazione.
    Usa UnitaryGate: corretto per qualsiasi N,a con gcd(a,N)=1.
    """
    n_work = ceil(log2(N + 1))
    size = 2 ** n_work
    a_pow = pow(a, power, N)
    # Matrice di permutazione: mat[y,x]=1 iff y = a_pow*x mod N
    mat = np.zeros((size, size), dtype=complex)
    for x in range(size):
        if x == 0 or x >= N:
            mat[x, x] = 1.0  # identità per 0 e fuori range
        else:
            y = (a_pow * x) % N
            mat[y, x] = 1.0
    gate = UnitaryGate(mat, label=f'{a}^{power} mod {N}')
    return gate.control(1, annotated=False)


# --- Shor circuit (QPE per N=15, N=21, N=35) ---
def shor_circuit(N, a, n_count):
    """
    Costruisce il circuito QPE per l'algoritmo di Shor.
    N=15: usa c_amod15 (loop-based, efficiente).
    N=21, N=35: usa c_amod (matrice di permutazione generale).
    """
    if N == 15:
        n_work = 4
        qc = QuantumCircuit(n_count + n_work, n_count)
        for q in range(n_count):
            qc.h(q)
        qc.x(n_count + 3)  # |1⟩ nella convenzione textbook (qubit MSB=1 → stato 8)
        for j in range(n_count):
            if 2 ** j % 4 != 0:
                qc.append(c_amod15(a, 2 ** j),
                           [j] + list(range(n_count, n_count + n_work)))
    else:
        if N not in [21, 35]:
            raise NotImplementedError(f"N={N} non supportato. Usa N in {{15, 21, 35}}.")
        # Beauregard e' validato con truth table e QPE separati. Nel circuito completo
        # N=21/a=2/n_count=8 la compilazione globale opt=2 produce 21.036 CX e
        # profondita' 23.081 nella base rz/sx/x/cx: troppo costoso per i rerun rumorosi.
        # Layout qubit Beauregard: [count | x(n) | b(n+1) | anc]
        n = ceil(log2(N + 1))
        n_b = n + 1
        n_total = n_count + n + n_b + 1   # ctrl_qubits + x + b + ancilla
        qc = QuantumCircuit(n_total, n_count)
        for q in range(n_count):
            qc.h(q)
        # Inizializza x a |1⟩: flip qubit MSB del registro x (qubit n_count + n - 1)
        qc.x(n_count + n - 1)
        for j in range(n_count):
            power = 2 ** j
            if pow(a, power, N) != 1:
                gate = beauregard_c_amod(a, N, power)
                # Qubits: ctrl=j, x=n_count..n_count+n-1, b=n_count+n..n_count+n+n_b-1, anc=last
                x_qubits = list(range(n_count, n_count + n))
                b_qubits = list(range(n_count + n, n_count + n + n_b))
                anc_qubit = [n_count + n + n_b]
                qc.append(gate, [j] + x_qubits + b_qubits + anc_qubit)

    qc.barrier()
    qc.append(inverse_qft(n_count), range(n_count))
    qc.measure(range(n_count), range(n_count))
    return qc


# --- Post-processing ---
def extract_factors(measured_value, n_count, N, a):
    if measured_value == 0:
        return None, None
    phase = measured_value / (2 ** n_count)
    frac = Fraction(phase).limit_denominator(N)
    r = frac.denominator
    if r % 2 != 0:
        return None, None
    p = gcd(a ** (r // 2) - 1, N)
    q = gcd(a ** (r // 2) + 1, N)
    if 1 < p < N:
        return p, N // p
    if 1 < q < N:
        return q, N // q
    return None, None


def rank_measurements(counts, tie_seed):
    """Ordina per frequenza con un tie-break riproducibile e non direzionale.

    L'ordine di inserimento dei dizionari Aer non e' una regola scientifica. Per
    conteggi uguali assegniamo quindi a ogni bitstring una priorita' SHA-256
    determinata dal seed della replica. In assenza di pareggi il risultato e'
    identico al normale ordinamento decrescente; nei pareggi evita di favorire
    sistematicamente gli esiti numericamente piccoli o grandi.
    """
    if isinstance(tie_seed, bool) or not isinstance(tie_seed, (int, np.integer)):
        raise TypeError('tie_seed deve essere un intero.')

    def tie_priority(bitstring):
        payload = f'{int(tie_seed)}:{bitstring}'.encode('ascii')
        return hashlib.sha256(payload).digest()

    return sorted(
        counts.items(),
        key=lambda item: (-float(item[1]), tie_priority(str(item[0]))),
    )


# --- Compilazione e provenienza sperimentale ---
@lru_cache(maxsize=32)
def compile_shor_circuit(N, a, n_count, optimization_level=2,
                         seed_transpiler=TRANSPILE_SEED):
    """Compila in una base esplicita e deterministica, riusabile tra i metodi.

    Senza ``basis_gates`` Aer puo' conservare H/CP/SWAP come istruzioni native e
    sottrarle involontariamente al modello di rumore. Il seed rende riproducibile
    anche la scelta fra decomposizioni equivalenti del transpiler.
    """
    return transpile(
        shor_circuit(N, a, n_count),
        basis_gates=list(BASIS_GATES),
        optimization_level=optimization_level,
        seed_transpiler=seed_transpiler,
    )


def circuit_fingerprint(circuit):
    """Hash stabile della sequenza di istruzioni compilata e dei relativi qubit."""
    instructions = []
    for item in circuit.data:
        op = item.operation
        instructions.append({
            'name': op.name,
            'params': [str(parameter) for parameter in op.params],
            'qubits': [circuit.find_bit(qubit).index for qubit in item.qubits],
            'clbits': [circuit.find_bit(clbit).index for clbit in item.clbits],
        })
    canonical = json.dumps(instructions, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def experiment_manifest(N=15, a=7, n_count=8, optimization_level=2):
    """Metadati minimi da salvare insieme a ogni nuovo artefatto sperimentale."""
    circuit = compile_shor_circuit(N, a, n_count, optimization_level)

    def package_version(name):
        try:
            return version(name)
        except PackageNotFoundError:
            return 'not-installed'

    return {
        'circuit_revision': CIRCUIT_REVISION,
        'noise_model_revision': NOISE_MODEL_REVISION,
        'postprocess_revision': POSTPROCESS_REVISION,
        'circuit_sha256': circuit_fingerprint(circuit),
        'basis_gates': list(BASIS_GATES),
        'optimization_level': int(optimization_level),
        'seed_transpiler': int(TRANSPILE_SEED),
        'depth': int(circuit.depth()),
        'size': int(circuit.size()),
        'gate_counts': {str(k): int(v) for k, v in circuit.count_ops().items()},
        'python': platform.python_version(),
        'packages': {
            'numpy': package_version('numpy'),
            'qiskit': package_version('qiskit'),
            'qiskit-aer': package_version('qiskit-aer'),
            'scikit-learn': package_version('scikit-learn'),
        },
    }


# --- Noise model ---
def _compose_errors(errors):
    combined = None
    for error in errors:
        if error is not None:
            combined = error if combined is None else combined.compose(error)
    return combined


def build_noise_model(eps_1q, eps_2q, t1_ns, t2_ns,
                      gate_time_ns=GATE_TIME_1Q_NS, p_ro=0.02,
                      gate_time_2q_ns=GATE_TIME_2Q_NS):
    """Modello uniforme illustrativo, non una calibrazione di una QPU reale.

    Il circuito va compilato con :func:`compile_shor_circuit`. RZ e' trattato
    come frame-change virtuale (durata/errore nulli); su SX/X si compongono
    depolarizzazione e rilassamento termico a 50 ns, su CX gli analoghi canali
    2Q a 300 ns. Il readout e' simmetrico con probabilita' ``p_ro``.
    """
    eps_1q = float(eps_1q)
    eps_2q = float(eps_2q)
    t1_ns = float(t1_ns)
    t2_ns = float(t2_ns)
    gate_time_ns = float(gate_time_ns)
    gate_time_2q_ns = float(gate_time_2q_ns)
    p_ro = float(p_ro)
    if not 0 <= eps_1q <= 1 or not 0 <= eps_2q <= 1:
        raise ValueError('eps_1q ed eps_2q devono essere in [0, 1].')
    if t1_ns <= 0 or t2_ns <= 0 or t2_ns > 2 * t1_ns:
        raise ValueError('Richiesti T1>0, T2>0 e T2<=2*T1.')
    if gate_time_ns <= 0 or gate_time_2q_ns <= 0:
        raise ValueError('Le durate dei gate devono essere positive.')
    if not 0 <= p_ro <= 1:
        raise ValueError('p_ro deve essere in [0, 1].')

    thermal_1q = thermal_relaxation_error(t1_ns, t2_ns, gate_time_ns)
    thermal_one_during_2q = thermal_relaxation_error(
        t1_ns, t2_ns, gate_time_2q_ns
    )
    thermal_2q = thermal_one_during_2q.tensor(thermal_one_during_2q)
    error_1q = _compose_errors([
        depolarizing_error(eps_1q, 1) if eps_1q else None,
        thermal_1q,
    ])
    error_2q = _compose_errors([
        depolarizing_error(eps_2q, 2) if eps_2q else None,
        thermal_2q,
    ])

    nm = NoiseModel()
    nm.add_all_qubit_quantum_error(error_1q, ['sx', 'x'])
    nm.add_all_qubit_quantum_error(error_2q, ['cx'])
    if p_ro:
        nm.add_all_qubit_readout_error(
            ReadoutError([[1 - p_ro, p_ro], [p_ro, 1 - p_ro]]))
    return nm


def _sim(noise_model=None):
    """AerSimulator MPS (matrix product state) — molto più veloce per circuiti profondi."""
    kw = {'method': 'matrix_product_state'}
    return AerSimulator(noise_model=noise_model, **kw) if noise_model else AerSimulator(**kw)


# ---------------------------------------------------------------------------
# SEEDING DELLE ITERAZIONI — leggere prima di modificare
#
# Aer deriva il seme di ogni shot da (seed_simulator + indice_shot). Con 1024 shot,
# due esecuzioni con semi consecutivi condividono 1023 campioni su 1024: sono di fatto
# LA STESSA esecuzione. Lo schema originario (seed * 10_000 + iterazione) rendeva quindi
# le iterazioni di una ripetizione fortemente correlate: se la moda del campione non
# produceva i fattori, non li produceva per nessuna delle 50 iterazioni, e la ripetizione
# esauriva il budget. Ne risultavano M_bar sovrastimato e tasso di successo sottostimato.
#
# Le iterazioni vanno separate di PIU' del numero di shot. Schema adottato:
#     seed_simulator = seed * 1_000_000 + iterazione * 10_000
# Verifica empirica: sovrapposizione dei conteggi fra semi distanti ~90% (valore atteso
# fra campioni indipendenti da una distribuzione concentrata), fra semi consecutivi 99.9%.
# ---------------------------------------------------------------------------

# --- Metodo 1 (TOP-1: picco più frequente per iterazione) ---
def run_method1(N, a, n_count, noise_model, shots=1024,
                max_iter=50, seed=42):
    sim = _sim(noise_model)
    transpiled = compile_shor_circuit(N, a, n_count)
    for iteration in range(1, max_iter + 1):
        simulation_seed = seed * 1_000_000 + iteration * 10_000
        counts = sim.run(transpiled, shots=shots,
                         seed_simulator=simulation_seed).result().get_counts()
        meas = int(rank_measurements(counts, simulation_seed)[0][0], 2)
        p, q = extract_factors(meas, n_count, N, a)
        if p is not None:
            return {'factors': (p, q), 'iterations': iteration, 'success': True,
                    'counts': counts}
    return {'factors': (None, None), 'iterations': max_iter, 'success': False,
            'counts': {}}


# --- Metodo 2 — classificatore ML + ricerca TOP-K ---
def run_method2(N, a, n_count, noise_model, classifier,
                shots=1024, max_iter=50, seed=42, top_k=4):
    """
    M2: il classificatore decide se l'istogramma ha segnale QPE recuperabile (top_k=4).
    Se clf=1, prova i top_k candidati più frequenti in ordine decrescente — cattura picchi
    QPE spostati dal rumore (es. mode=65 invece di 64). Se clf=0, l'istogramma è piatto:
    nessun candidato sarebbe affidabile, si salta l'iterazione.
    """
    sim = _sim(noise_model)
    transpiled = compile_shor_circuit(N, a, n_count)
    for iteration in range(1, max_iter + 1):
        simulation_seed = seed * 1_000_000 + iteration * 10_000
        counts = sim.run(transpiled, shots=shots,
                         seed_simulator=simulation_seed).result().get_counts()
        feature = np.zeros(2 ** n_count)
        for k, v in counts.items():
            feature[int(k, 2)] = v / shots
        if classifier.predict([feature])[0] == 0:
            continue  # Istogramma troppo rumoroso: salta iterazione
        # Prova i top_k candidati più frequenti
        sorted_meas = rank_measurements(counts, simulation_seed)
        for meas_str, _ in sorted_meas[:top_k]:
            p, q = extract_factors(int(meas_str, 2), n_count, N, a)
            if p is not None:
                return {'factors': (p, q), 'iterations': iteration, 'success': True}
    return {'factors': (None, None), 'iterations': max_iter, 'success': False}
