"""Backend per la demo interattiva del codice di Steane [[7,1,3]]: inietta un errore Pauli su
un qubit dati a scelta e osserva sindrome, correzione decodificata ed esito.

Riusa `qec_steane.py` (Extra/experiments/M6_steane_code) — lo stesso codice della campagna
ufficiale M6 (encoding, misura di sindrome già verificati biiettivi) — non una reimplementazione
parallela. Stessa cautela di quantum_backend.py: ogni chiamata ad AerSimulator gira in un
sottoprocesso dedicato (Aer nel thread di Streamlit non è garantito stabile).
"""
import json
import os
import subprocess
import sys

_STEANE_DIR = os.path.join(os.path.dirname(__file__), "..", "experiments", "M6_steane_code")
sys.path.insert(0, os.path.abspath(_STEANE_DIR))
from qec_steane import build, _parse, GZ, GX  # noqa: E402

DATA_QUBITS = list(range(7))


def decode(sz, sx):
    """sz, sx: tuple di 3 bit. Ritorna (qubit_x, qubit_y_z) — indice 0-6 del qubit su cui la
    sindrome indica un errore X e/o Z (None se quella sindrome e' 000, nessun errore di quel tipo)."""
    vz = sz[0] * 4 + sz[1] * 2 + sz[2]
    vx = sx[0] * 4 + sx[1] * 2 + sx[2]
    q_x = vz - 1 if vz > 0 else None   # sindrome Z -> corregge un errore X sul qubit q_x
    q_z = vx - 1 if vx > 0 else None   # sindrome X -> corregge un errore Z sul qubit q_z
    return q_x, q_z


def run_injection(pauli, qubit, seed=42):
    """pauli: 'X'|'Y'|'Z'|None. qubit: 0-6 (ignorato se pauli None). Ritorna un dict con
    sindrome, qubit/tipo identificato dalla decodifica, e verifica di correttezza."""
    inject = None if pauli is None else (pauli, qubit)
    qc = build(inject=inject)
    from qiskit import transpile
    from qiskit_aer import AerSimulator
    sim = AerSimulator()
    tqc = transpile(qc, sim, optimization_level=0)
    counts = sim.run(tqc, shots=1, seed_simulator=seed).result().get_counts()
    bitstring = next(iter(counts))
    sz, sx = _parse(bitstring)
    q_x, q_z = decode(sz, sx)

    if pauli is None:
        expected_ok = q_x is None and q_z is None
        identified = "nessun errore"
        correction = "nessuna"
    elif pauli == "X":
        expected_ok = (q_x == qubit) and (q_z is None)
        identified = f"X sul qubit {q_x}" if q_x is not None else "nessuno (ERRORE)"
        correction = f"X sul qubit {q_x}" if q_x is not None else "--"
    elif pauli == "Z":
        expected_ok = (q_z == qubit) and (q_x is None)
        identified = f"Z sul qubit {q_z}" if q_z is not None else "nessuno (ERRORE)"
        correction = f"Z sul qubit {q_z}" if q_z is not None else "--"
    else:  # Y
        expected_ok = (q_x == qubit) and (q_z == qubit)
        identified = f"Y sul qubit {qubit}" if (q_x == qubit and q_z == qubit) else "incompleto (ERRORE)"
        correction = f"Y sul qubit {qubit}" if (q_x == qubit and q_z == qubit) else "--"

    return {
        "pauli": pauli, "qubit": qubit, "sz": sz, "sx": sx,
        "q_x": q_x, "q_z": q_z, "identified": identified, "correction": correction,
        "recovered": bool(expected_ok),
    }


# ---------------------------------------------------------------------------
# Isolamento in sottoprocesso (stesso motivo di quantum_backend.py).
# ---------------------------------------------------------------------------
def _run_worker(params, timeout=60):
    proc = subprocess.run(
        [sys.executable, os.path.abspath(__file__)],
        input=json.dumps(params), capture_output=True, text=True, timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Simulazione Steane fallita nel sottoprocesso:\n{proc.stderr[-4000:]}")
    return json.loads(proc.stdout)


def run_injection_isolated(pauli, qubit, seed=42):
    return _run_worker({"pauli": pauli, "qubit": qubit, "seed": seed})


if __name__ == "__main__":
    params = json.loads(sys.stdin.read())
    out = run_injection(params["pauli"], params["qubit"], params["seed"])
    print(json.dumps(out))
