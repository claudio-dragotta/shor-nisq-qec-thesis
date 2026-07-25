"""Caricamento dei risultati sperimentali già presenti in Extra/experiments/.

Nessuna dipendenza da Qiskit/Stim/WSL: la demo legge i JSON prodotti dalle
campagne (M1-M8) e i numeri già validati e riportati in tesi. Non ricalcola
nulla dal vivo, per essere eseguibile ovunque (anche in discussione di tesi).
"""
import json
from pathlib import Path

import numpy as np

EXP_DIR = Path(__file__).resolve().parent.parent / "experiments"


def _load_first(subdir: str, glob_pattern: str, key: str | None = None) -> dict:
    """Carica il primo file che matcha glob_pattern in subdir; se key è dato,
    tra più file con lo stesso pattern sceglie quello che contiene quella chiave."""
    folder = EXP_DIR / subdir
    matches = sorted(folder.glob(glob_pattern))
    if not matches:
        raise FileNotFoundError(f"Nessun file '{glob_pattern}' in {folder}")
    if key is None:
        return json.loads(matches[0].read_text(encoding="utf-8"))
    for m in matches:
        d = json.loads(m.read_text(encoding="utf-8"))
        if key in d:
            return d
    raise FileNotFoundError(f"Nessun file con chiave '{key}' in {folder}/{glob_pattern}")


def load_m5(basis: str) -> dict:
    """M5 - repetition code, basis 'X' o 'Z'."""
    return _load_first("M5_repetition_code", f"results_M5_repetition_{basis}_*.json")


def load_m6_curve() -> dict:
    return _load_first("M6_steane_code", "results_M6_steane_*.json", key="curve")


def load_m6_verify() -> dict:
    return _load_first("M6_steane_code", "results_M6_steane_*.json", key="verify")


def load_m6_check() -> dict:
    return _load_first("M6_steane_code", "results_M6_steane_*.json", key="check")


def load_m7(basis: str) -> dict:
    """M7 - surface code, basis 'x' o 'z'."""
    return _load_first("M7_surface_code", f"results_M7_surface_{basis}_*.json")


def load_m8() -> dict:
    return _load_first("M8_shor_logico", "results_M8_shor_logico_*.json")


# --- Numeri "di cornice", non ricalcolabili da un JSON isolato: sono i valori
# già validati e riportati nel Cap. 10 (RisultatiSperimentali.tex, tab:riepilogo_rho)
# e nel Cap. 13 (ShorLogico.tex, fig:qec_shor_logico). Riportati qui letteralmente,
# non stimati, per tenere la demo in sincrono con la tesi.

ABLATION_TABLE = [
    # UC, variante, P_succ (%), M_bar, rho vs M1, p-value vs M1
    ("UC1", "M1 (TOP-1)", 76.7, 6.43, None, None),
    ("UC1", "M_TOP4 (no clf)", 100.0, 1.00, 6.435, "<0.001"),
    ("UC1", "M2 (CLF+TOP-4)", 96.7, 1.00, 6.435, "0.0002"),
    ("UC2", "M1 (TOP-1)", 80.0, 2.42, None, None),
    ("UC2", "M_TOP4 (no clf)", 100.0, 1.00, 2.417, "0.003"),
    ("UC2", "M2 (CLF+TOP-4)", 76.7, 3.30, 0.731, "0.704 (n.s.)"),
]
ABLATION_NOTE_UC1 = "M_TOP4 vs M2 (Mann-Whitney): p = 0.849 — non significativo. Il guadagno è del TOP-4, non del classificatore."
ABLATION_NOTE_UC2 = "M_TOP4 vs M2 (Mann-Whitney): p < 0.001 — M2 è significativamente peggiore di M_TOP4 (classificatore dannoso)."

USE_CASES = [
    # N, a, r_atteso, n_count, M_shots, livello_rumore, eps1q, eps2q, T1_ns, T2_ns, p_ro
    ("UC1", 15, 7, 4, 8, 4096, "NISQ-realistico", 1e-3, 1e-2, 100_000, 80_000, 0.02),
    ("UC2", 15, 7, 4, 8, 4096, "NISQ-degradato", 5e-3, 5e-2, 50_000, 30_000, 0.05),
    ("UC3", 21, 2, 6, 10, 4096, "NISQ-realistico", 1e-3, 1e-2, 100_000, 80_000, 0.02),
    ("UC4", 35, 6, 2, 12, 4096, "NISQ-realistico", 1e-3, 1e-2, 100_000, 80_000, 0.02),
]

SHOR_LOGICO_REGIMES = [
    # etichetta, p_L, P_success (dal testo del Cap. 13, non dal JSON puntuale)
    ("Shor fisico nudo (nessuna correzione)", 1e-2, 0.64),
    ("Codice di Steane [[7,1,3]]", 1.7e-3, 0.72),
    ("Surface code d=7 (sotto soglia)", 1e-4, 0.74),
]


def project_qec_outcome(p_2q: float) -> dict:
    """Proiezione (per interpolazione sulle curve GIA' validate M6/M7/M8) di che cosa
    succederebbe alla probabilita' di successo di Shor se un errore fisico a 2 qubit p_2q
    fosse corretto dal codice di Steane oppure dal surface code (d=7, base Z).

    Non e' una nuova simulazione fault-tolerant esplicita (intrattabile per lo Shor logico,
    cfr. Cap. 13): e' la stessa logica "a canale unico" usata in M8, applicata qui a un
    p_2q scelto dall'utente invece che ai punti fissi della campagna.
    """
    m6_points = load_m6_curve()["curve"]["points"]
    m7z_points = load_m7("z")["curve"]["table"]["7"]
    m8_points = load_m8()["curve"]["points"]

    def interp_p_to_pl(points, p):
        ps = [pt["p"] for pt in points]
        pls = [pt["p_L"] for pt in points]
        return float(np.interp(p, ps, pls))

    def interp_pl_to_psucc(points, pl):
        pls = [pt["p_L"] for pt in points]
        psuccs = [pt["P_success"] for pt in points]
        return float(np.interp(pl, pls, psuccs))

    pl_steane = interp_p_to_pl(m6_points, p_2q)
    pl_surface = interp_p_to_pl(m7z_points, p_2q)
    return {
        "p_2q": p_2q,
        "fisico": {"p_L": p_2q, "P_success": interp_pl_to_psucc(m8_points, p_2q)},
        "steane": {"p_L": pl_steane, "P_success": interp_pl_to_psucc(m8_points, pl_steane)},
        "surface_d7": {"p_L": pl_surface, "P_success": interp_pl_to_psucc(m8_points, pl_surface)},
    }
