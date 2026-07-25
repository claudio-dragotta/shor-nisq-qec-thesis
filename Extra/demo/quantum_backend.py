"""Backend per il simulatore live: esegue il VERO circuito di Shor (N=15, a=7) della tesi
con Qiskit + Qiskit Aer, con rumore configurabile globale, per-qubit e per-gate (istanza
esatta nel circuito trasposto).

Riusa `shor_core.py` (Extra/experiments/campagne_classiche_M1-M4) — la stessa libreria delle
campagne ufficiali M1-M4 — così il simulatore live è metodologicamente identico ai risultati
già in tesi, non un'implementazione parallela.
"""
import json
import os
import subprocess
import sys

from qiskit import transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import depolarizing_error

_CORE_DIR = os.path.join(os.path.dirname(__file__), "..", "experiments", "campagne_classiche_M1-M4")
sys.path.insert(0, os.path.abspath(_CORE_DIR))
from shor_core import shor_circuit, extract_factors, build_noise_model  # noqa: E402

N, A, N_COUNT = 15, 7, 8  # istanza dimostrativa della tesi (Cap. 13): N=15, a=7, periodo r=4
N_WORK = 4
QUBIT_LABELS = [f"count[{i}]" for i in range(N_COUNT)] + [f"work[{i}]" for i in range(N_WORK)]


def build_base_circuit():
    return shor_circuit(N, A, N_COUNT)


def base_circuit_layers():
    """Struttura a livelli (moment) del circuito BASE (non trasposto) per il disegno custom:
    lista di layer, ciascuno lista di {'name', 'qubits'}. Usa solo Qiskit-core (circuit_to_dag,
    nessun AerSimulator) — gira in-process senza il rischio di crash del sottoprocesso Aer,
    perché non istanzia nessun simulatore."""
    from qiskit.converters import circuit_to_dag
    qc = build_base_circuit()
    dag = circuit_to_dag(qc)
    layers = []
    for layer in dag.layers():
        ops = []
        for node in layer["graph"].op_nodes():
            qubits = [qc.find_bit(q).index for q in node.qargs]
            name = node.op.name
            if name.startswith("QFT"):
                name = "QFT⁻¹"  # QFT^-1, evita il carattere mangled di Qiskit
            ops.append({"name": name, "qubits": qubits})
        layers.append(ops)
    return layers


def transpile_for(noise_model, seed=42):
    """Trasposizione contro il simulatore rumoroso target — stessa metodologia di shor_core
    (run_method1/2): decompone CCX->CX+RZ+H per essere coerente col modello di rumore."""
    sim = AerSimulator(noise_model=noise_model, method="matrix_product_state")
    return transpile(build_base_circuit(), sim, optimization_level=2, seed_transpiler=seed)


def list_gates(tqc):
    """Righe selezionabili nella tabella del circuito: indice, nome, qubit coinvolti."""
    rows = []
    for i, instr in enumerate(tqc.data):
        name = instr.operation.name
        if name in ("barrier", "measure"):
            continue
        qubits = [tqc.find_bit(q).index for q in instr.qubits]
        rows.append({
            "index": i,
            "gate": name,
            "qubit(s)": ", ".join(QUBIT_LABELS[q] for q in qubits),
            "n_qubit": len(qubits),
        })
    return rows


def inject_gate_noise(tqc, gate_indices, extra_p):
    """Ricostruisce il circuito inserendo un canale depolarizzante extra_p subito DOPO ogni
    istanza di gate selezionata (per indice esatto, non per nome) — non un NoiseModel globale,
    ma un'iniezione chirurgica nella singola posizione del circuito."""
    gate_indices = set(gate_indices)
    if not gate_indices or extra_p <= 0:
        return tqc
    new_qc = tqc.copy_empty_like()
    for i, instr in enumerate(tqc.data):
        new_qc.append(instr.operation, instr.qubits, instr.clbits)
        if i in gate_indices:
            k = len(instr.qubits)
            if k in (1, 2):
                err = depolarizing_error(min(extra_p, 1.0 - 1e-9), k)
                new_qc.append(err.to_instruction(), instr.qubits)
    return new_qc


def gates_touching_qubits(gate_rows, qubit_indices):
    qubit_indices = set(qubit_indices)
    out = set()
    for row in gate_rows:
        row_qubits = {QUBIT_LABELS.index(lbl) for lbl in row["qubit(s)"].split(", ")}
        if row_qubits & qubit_indices:
            out.add(row["index"])
    return out


def run_comparison(eps_1q, eps_2q, t1_ns, t2_ns, p_ro, gate_indices, extra_p, shots, seed):
    """Esegue lo STESSO circuito (stesso seed) senza rumore e con il rumore configurato.
    Ritorna: gate_rows, ideal_counts, noisy_counts, tqc (per riuso/debug)."""
    nm = build_noise_model(eps_1q, eps_2q, t1_ns, t2_ns, p_ro=p_ro)
    tqc = transpile_for(nm, seed=seed)
    gate_rows = list_gates(tqc)

    tqc_noisy = inject_gate_noise(tqc, gate_indices, extra_p)

    sim_ideal = AerSimulator(method="matrix_product_state")
    sim_noisy = AerSimulator(noise_model=nm, method="matrix_product_state")

    ideal_counts = sim_ideal.run(tqc, shots=shots, seed_simulator=seed).result().get_counts()
    noisy_counts = sim_noisy.run(tqc_noisy, shots=shots, seed_simulator=seed).result().get_counts()

    return gate_rows, ideal_counts, noisy_counts


def top_k_outcomes(counts, k=4):
    return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:k]


def factor_verdict(counts, k=4):
    """Per ogni esito TOP-k, prova extract_factors; ritorna la lista con esito e successo."""
    rows = []
    for meas_str, n in top_k_outcomes(counts, k):
        p, q = extract_factors(int(meas_str, 2), N_COUNT, N, A)
        success = p is not None
        rows.append({
            "esito (binario)": meas_str,
            "conteggio": n,
            "fattori": f"{p} x {q}" if success else "--",
            "successo": success,
        })
    return rows


def top1_success(counts):
    meas_str = max(counts, key=counts.get)
    p, _ = extract_factors(int(meas_str, 2), N_COUNT, N, A)
    return p is not None


def top4_success(counts):
    return any(r["successo"] for r in factor_verdict(counts, k=4))


def bit_marginals(counts, n_bits=N_COUNT):
    """P(bit_i = 1) per ciascun bit i del registro classico misurato (0=MSB come nelle
    stringhe di Qiskit), marginalizzando sugli shot. Serve a mostrare QUALI qubit misurati
    sono stati disturbati dal rumore, confrontando ideale vs rumoroso bit per bit."""
    total = sum(counts.values())
    if total == 0:
        return [0.0] * n_bits
    probs = [0.0] * n_bits
    for bitstring, n in counts.items():
        for i, ch in enumerate(bitstring):
            if ch == "1":
                probs[i] += n
    return [p / total for p in probs]


# ---------------------------------------------------------------------------
# Isolamento in sottoprocesso.
#
# Qiskit Aer (metodo matrix_product_state) va in Segmentation fault se costruito
# ed eseguito nel thread interno di ScriptRunner di Streamlit (riprodotto: stessa
# identica chiamata, stessi parametri, funziona sempre se lanciata come processo
# python normale — anche ripetuta 15 volte di fila — ma crasha sistematicamente
# dentro il thread di Streamlit). Per aggirarlo, ogni chiamata a Qiskit gira in un
# sottoprocesso python dedicato (interprete proprio, thread principale proprio).
# ---------------------------------------------------------------------------
def _run_worker(mode, params, timeout=90):
    proc = subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--mode", mode],
        input=json.dumps(params), capture_output=True, text=True, timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Simulazione fallita nel sottoprocesso:\n{proc.stderr[-4000:]}")
    return json.loads(proc.stdout)


def list_gates_isolated(eps_1q, eps_2q, t1_ns, t2_ns, p_ro, seed):
    out = _run_worker("gates", dict(
        eps_1q=eps_1q, eps_2q=eps_2q, t1_ns=t1_ns, t2_ns=t2_ns, p_ro=p_ro, seed=seed,
    ))
    return out["gate_rows"]


def run_comparison_isolated(eps_1q, eps_2q, t1_ns, t2_ns, p_ro, gate_indices, extra_p, shots, seed):
    out = _run_worker("compare", dict(
        eps_1q=eps_1q, eps_2q=eps_2q, t1_ns=t1_ns, t2_ns=t2_ns, p_ro=p_ro,
        gate_indices=sorted(gate_indices), extra_p=extra_p, shots=shots, seed=seed,
    ))
    return out["gate_rows"], out["ideal_counts"], out["noisy_counts"]


def _cli_main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["gates", "compare"], required=True)
    args = ap.parse_args()
    params = json.loads(sys.stdin.read())

    if args.mode == "gates":
        nm = build_noise_model(params["eps_1q"], params["eps_2q"], params["t1_ns"],
                                params["t2_ns"], p_ro=params["p_ro"])
        tqc = transpile_for(nm, seed=params["seed"])
        print(json.dumps({"gate_rows": list_gates(tqc)}))
    else:
        gate_rows, ideal_counts, noisy_counts = run_comparison(
            params["eps_1q"], params["eps_2q"], params["t1_ns"], params["t2_ns"], params["p_ro"],
            set(params["gate_indices"]), params["extra_p"], params["shots"], params["seed"],
        )
        print(json.dumps({
            "gate_rows": gate_rows, "ideal_counts": ideal_counts, "noisy_counts": noisy_counts,
        }))


if __name__ == "__main__":
    _cli_main()
