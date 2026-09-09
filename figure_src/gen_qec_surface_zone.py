"""
gen_qec_surface_zone.py — Figura M7: surface code con zone operative colorate.

Versione estesa di gen_qec_surface.py: aggiunge sfondo verde (sotto soglia,
QEC sopprime gli errori) e rosso (sopra soglia, QEC li amplifica), rendendo
visivamente esplicita la transizione di fase che il codice a superficie attraversa.

Non modifica gen_qec_surface.py esistente: produce 'gen_qec_surface_zone.pdf'
in file_latex/figure e l'anteprima .png in figure_src/anteprime.

Usa entrambe le basi (Z e X) per mostrare la robustezza della soglia.

Gli input sono espliciti: nessuna selezione implicita del file piu' recente.
I default puntano ai JSON M7 canonici a quattro distanze (d = 3, 5, 7, 9); i
file del 31/07/2026 ne contengono solo tre e non sostengono la legge di scala
discussa nel capitolo.

Uso (ambiente canonico):
    /home/claudio/quantum-env/bin/python figure_src/gen_qec_surface_zone.py
    /home/claudio/quantum-env/bin/python figure_src/gen_qec_surface_zone.py \
        --input-z <file_z.json> --input-x <file_x.json>
"""
import argparse
import json
import os

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── Percorsi ─────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.join(_HERE, "..")
EXP_DIR = os.path.join(_ROOT, "Extra", "experiments", "M7_surface_code")
OUT_DIR = os.path.join(_ROOT, "file_latex", "figure")
PNG_DIR = os.path.join(_HERE, "anteprime")

# JSON M7 canonici, indicati per nome esatto: la regola sui generatori vieta di
# lasciare che sia il glob a scegliere.
DEFAULT_Z = "results_M7_surface_z_20260808_001903.json"
DEFAULT_X = "results_M7_surface_x_20260808_002307.json"


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Figura M7 con zone operative colorate.")
    ap.add_argument("--input-z", default=os.path.join(EXP_DIR, DEFAULT_Z),
                    help="JSON M7 base Z (default: %(default)s)")
    ap.add_argument("--input-x", default=os.path.join(EXP_DIR, DEFAULT_X),
                    help="JSON M7 base X (default: %(default)s)")
    return ap.parse_args()


def _load(path: str, basis: str) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"JSON M7 base={basis} non trovato: {path}. "
            f"Indicarlo con --input-{basis}, oppure eseguire qec_surface.py."
        )
    with open(path) as f:
        return json.load(f)


_args = _parse_args()
data_z = _load(_args.input_z, "z")
data_x = _load(_args.input_x, "x")
print(f"[gen_qec_surface_zone] base Z <- {os.path.basename(_args.input_z)}")
print(f"[gen_qec_surface_zone] base X <- {os.path.basename(_args.input_x)}")

table_z   = data_z["curve"]["table"]
table_x   = data_x["curve"]["table"]
p_th_z    = float(data_z["curve"]["threshold"])   # niente fallback: deve venire dal JSON
p_th_x    = float(data_x["curve"]["threshold"])   # niente fallback: deve venire dal JSON
distances = sorted(int(d) for d in table_z)

# ── Palette ──────────────────────────────────────────────────────────────────
COLORS  = {3: "#1565C0", 5: "#2E7D32", 7: "#E65100", 9: "#6A1B9A"}
MARKERS = {3: "o", 5: "s", 7: "^", 9: "D"}
LINESTYLES = {"z": "-", "x": "--"}

C_SAFE   = "#43A047"   # verde — sotto soglia (QEC sopprime)
C_UNSAFE = "#E53935"   # rosso — sopra soglia (QEC amplifica)

# ── Figura ───────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), sharey=False)

for ax, (data, p_th, basis_label) in zip(
    axes,
    [(data_z, p_th_z, "Z"), (data_x, p_th_x, "X")],
):
    table = data["curve"]["table"]

    # Tutti i punti per determinare i limiti degli assi
    all_p  = [r["p"]   for pts in table.values() for r in pts]
    all_pL = [r["p_L"] for pts in table.values() for r in pts]
    p_lo, p_hi = min(all_p) * 0.85, max(all_p) * 1.15

    # ── Zone colorate ────────────────────────────────────────────────────────
    # Sotto soglia → verde (QEC aiuta: d più grande → p_L più piccolo)
    ax.axvspan(p_lo, p_th, color=C_SAFE,   alpha=0.10, zorder=0)
    # Sopra soglia → rosso (QEC peggiora: d più grande → p_L più grande)
    ax.axvspan(p_th, p_hi, color=C_UNSAFE, alpha=0.10, zorder=0)

    # Linea di soglia
    ax.axvline(p_th, color="#424242", ls=":", lw=1.2, zorder=1)
    ax.text(
        p_th * 0.93, min(all_pL) * 1.05,
        f"$p_{{th}}\\approx{p_th:.3f}$",
        fontsize=8.0, color="#424242", ha="right", rotation=90,
        va="bottom", zorder=5,
    )

    # ── Annotazioni zone ─────────────────────────────────────────────────────
    p_mid_safe   = np.sqrt(p_lo * p_th)
    p_mid_unsafe = np.sqrt(p_th * p_hi)
    y_top = max(all_pL) * 1.5
    ax.text(p_mid_safe,   y_top, "QEC sopprime\n↑ d  →  ↓ $p_L$",
            ha="center", va="top", fontsize=7.5,
            color=C_SAFE,   alpha=0.85, zorder=5)
    ax.text(p_mid_unsafe, y_top, "QEC amplifica\n↑ d  →  ↑ $p_L$",
            ha="center", va="top", fontsize=7.5,
            color=C_UNSAFE, alpha=0.85, zorder=5)

    # ── Curve p_L per distanza ────────────────────────────────────────────────
    for d in distances:
        if str(d) not in table:
            continue
        pts = table[str(d)]
        p   = np.array([r["p"]      for r in pts])
        pL  = np.array([r["p_L"]    for r in pts])
        se  = np.array([r["p_L_se"] for r in pts])
        ax.errorbar(
            p, pL, yerr=se,
            fmt=MARKERS.get(d, "o") + "-",
            color=COLORS.get(d, "gray"),
            ms=5.5, capsize=2.0, lw=1.4,
            label=f"$d={d}$",
            zorder=3,
        )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"tasso di errore fisico $p$ (circuit-level)", fontsize=9.5)
    ax.set_ylabel(r"tasso di errore logico $p_L$", fontsize=9.5)
    ax.set_title(
        f"Surface code — base {basis_label} — decoder MWPM",
        fontsize=9.5,
    )
    ax.legend(fontsize=8.5, title="distanza $d$", title_fontsize=8.0,
              framealpha=0.9, loc="upper left")
    ax.grid(alpha=0.22, which="both", lw=0.55)
    ax.set_xlim(p_lo, p_hi)

# Legenda zone (globale in basso)
zone_handles = [
    mpatches.Patch(color=C_SAFE,   alpha=0.55,
                   label=r"sotto soglia: $\uparrow d \Rightarrow \downarrow p_L$ (QEC sopprime)"),
    mpatches.Patch(color=C_UNSAFE, alpha=0.55,
                   label=r"sopra soglia: $\uparrow d \Rightarrow \uparrow p_L$ (QEC amplifica)"),
]
fig.legend(handles=zone_handles, loc="lower center", ncol=2,
           fontsize=8.5, framealpha=0.9, bbox_to_anchor=(0.5, -0.06))

fig.suptitle(
    r"M7 — Transizione di fase del surface code (basi Z e X, $d \in \{3,5,7,9\}$)",
    fontsize=10.5, y=1.02,
)
fig.tight_layout()

os.makedirs(OUT_DIR, exist_ok=True)
base = os.path.join(OUT_DIR, "gen_qec_surface_zone")
fig.savefig(base + ".pdf", bbox_inches="tight")
os.makedirs(PNG_DIR, exist_ok=True)
fig.savefig(os.path.join(PNG_DIR, os.path.basename(base) + ".png"),
            dpi=180, bbox_inches="tight")
print(f"Salvato: {base}.pdf")
print(f"Anteprima: {os.path.join(PNG_DIR, os.path.basename(base))}.png")
