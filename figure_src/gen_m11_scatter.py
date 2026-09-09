"""
gen_m11_scatter.py — Figura M11: generalizzazione layout (train vs holdout).

Mostra i 40 layout validi come punti (P_success train vs P_success holdout),
evidenziando i due layout selezionati: per fidelità hardware (layout 35)
e per score sul train (layout 48). La diagonale y=x è il caso ideale.

Uso (ambiente canonico):
    /home/claudio/quantum-env/bin/python figure_src/gen_m11_scatter.py
"""
import json
import os

import matplotlib.pyplot as plt
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.join(_HERE, "..")
ARTIFACT = os.path.join(
    _ROOT,
    "Extra/experiments/M11_layout/artifacts/v2_20260819",
    "results_M11_pilota_v2_20260826_222137.json",
)
OUT_DIR = os.path.join(_ROOT, "file_latex", "figure")
PNG_DIR = os.path.join(_HERE, "anteprime")

with open(ARTIFACT) as f:
    data = json.load(f)

points = data["points"]
stats  = data["statistics"]

train_p   = np.array([p["train"]["P_success"]      for p in points])
holdout_p = np.array([p["holdout"]["P_success"]    for p in points])
train_se  = np.array([p["train"]["P_success_se"]   for p in points])
hold_se   = np.array([p["holdout"]["P_success_se"] for p in points])

SEL_FID   = stats["selected_by_fidelity_layout_id"]   # 35
SEL_TRAIN = stats["selected_on_train_layout_id"]       # 48
idx_fid   = next(i for i, p in enumerate(points) if p["layout_id"] == SEL_FID)
idx_train = next(i for i, p in enumerate(points) if p["layout_id"] == SEL_TRAIN)

C_ALL  = "#6B9DC2"
C_FID  = "#2E7D32"
C_TR   = "#E65100"
C_DIAG = "#757575"

fig, ax = plt.subplots(figsize=(5.8, 5.0))

lo = min(train_p.min(), holdout_p.min()) - 0.015
hi = max(train_p.max(), holdout_p.max()) + 0.015
diag = np.array([lo, hi])
ax.fill_between(diag, diag - 0.02, diag + 0.02,
                color=C_DIAG, alpha=0.08, zorder=0)
ax.plot(diag, diag, color=C_DIAG, ls="--", lw=1.0, alpha=0.55,
        label=r"$P_\mathrm{holdout} = P_\mathrm{train}$")

mask = np.ones(len(points), dtype=bool)
mask[idx_fid] = False
mask[idx_train] = False
ax.errorbar(
    train_p[mask], holdout_p[mask],
    xerr=train_se[mask], yerr=hold_se[mask],
    fmt="o", color=C_ALL, alpha=0.55, ms=5.5,
    capsize=2.0, lw=0.7, ecolor=C_ALL + "99",
    label="layout validi (n=40)", zorder=2,
)

ax.errorbar(
    [train_p[idx_fid]], [holdout_p[idx_fid]],
    xerr=[train_se[idx_fid]], yerr=[hold_se[idx_fid]],
    fmt="D", color=C_FID, ms=9.5, capsize=3.0, lw=1.2,
    label=f"selezionato per fidelità hardware (layout {SEL_FID})", zorder=4,
)
ax.errorbar(
    [train_p[idx_train]], [holdout_p[idx_train]],
    xerr=[train_se[idx_train]], yerr=[hold_se[idx_train]],
    fmt="s", color=C_TR, ms=9.5, capsize=3.0, lw=1.2,
    label=f"selezionato per score sul train (layout {SEL_TRAIN})", zorder=4,
)

for idx, col in [(idx_fid, C_FID), (idx_train, C_TR)]:
    ax.annotate(
        f"$P_{{h}}={holdout_p[idx]:.3f}$",
        xy=(train_p[idx], holdout_p[idx]),
        xytext=(6, -14), textcoords="offset points",
        fontsize=7.5, color=col,
    )

ax.set_xlim(lo, hi)
ax.set_ylim(lo, hi)
ax.set_xlabel(r"$P_\mathrm{success}$ — train", fontsize=10)
ax.set_ylabel(r"$P_\mathrm{success}$ — holdout", fontsize=10)
ax.set_title(
    "M11 — Generalizzazione layout: train vs holdout\n"
    r"FakeSherbrooke 127 qubit, circuito Shor $N=15$",
    fontsize=9.5,
)
ax.legend(fontsize=7.5, loc="upper left", framealpha=0.92)
ax.grid(alpha=0.25, lw=0.6)

sp = stats["spearman_score_vs_holdout"]
ax.text(
    0.02, 0.02,
    f"ρ={sp['estimate']:.3f} [{sp['ci_low']:.3f}, {sp['ci_high']:.3f}] 95% CI (Spearman)",
    transform=ax.transAxes, fontsize=7.0, color="#555555", va="bottom",
)

fig.tight_layout()
os.makedirs(OUT_DIR, exist_ok=True)
base = os.path.join(OUT_DIR, "gen_m11_scatter")
fig.savefig(base + ".pdf", bbox_inches="tight")
os.makedirs(PNG_DIR, exist_ok=True)
fig.savefig(os.path.join(PNG_DIR, os.path.basename(base) + ".png"),
            dpi=180, bbox_inches="tight")
print(f"Salvato: {base}.pdf")
print(f"Anteprima: {os.path.join(PNG_DIR, os.path.basename(base))}.png")
