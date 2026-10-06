"""Rigenera i cinque grafici dei risultati (slide 13-16 e 18) in formato uniforme.

Stessa tela (10,4 x 6,2 pollici), stessi corpi e stessa palette di genera_immagini.py;
i cerchi arancioni di evidenza sono disegnati nel grafico, non più sovrapposti in
PowerPoint. Valori dalle tabelle del Capitolo 5 di file_latex_v2; la slide 15 legge i
JSON M7 (Extra/experiments/M7_surface_code), gli stessi della figura 5.4.

    python genera_grafici_v2.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mt
from matplotlib.patches import FancyBboxPatch

QUI = Path(__file__).resolve().parent
M7 = QUI.parents[2] / "Extra" / "experiments" / "M7_surface_code"

BLU = "#125C97"
ARANCIO = "#D9822B"
SCURO = "#0B2F5B"
GRIGIO = "#5B6573"
GRIGIO_CHIARO = "#9AA5B1"
GRIGLIA = "#E3E8EE"
TESTO = "#1F2933"
FIGSIZE = (10.4, 6.2)

plt.rcParams.update({
    "font.family": "Arial", "font.size": 22, "axes.labelsize": 24,
    "xtick.labelsize": 22, "ytick.labelsize": 22, "legend.fontsize": 20,
    "axes.edgecolor": GRIGIO, "axes.labelcolor": TESTO,
    "xtick.color": TESTO, "ytick.color": TESTO,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.formatter.use_locale": False,
})


def virgola(fmt):
    return mt.FuncFormatter(lambda v, _: format(v, fmt).replace(".", ","))


def cerchio(ax, x, y, s=900):
    ax.scatter([x], [y], s=s, facecolors="none", edgecolors=ARANCIO,
               linewidths=3, zorder=5)


def salva(fig, nome):
    fig.savefig(QUI / nome, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# --- Slide 13: successo di Shor contro p_g (Tab. 5.19) ------------------------
pg = [1e-4, 5e-4, 1e-3, 1.7e-3, 2e-3, 5e-3, 1e-2, 2e-2, 5e-2, 1e-1, 2e-1, 5e-1]
ps = [0.7469, 0.7373, 0.7250, 0.7083, 0.6992, 0.6450, 0.5651, 0.4518,
      0.2953, 0.2503, 0.2441, 0.2459]
fig, ax = plt.subplots(figsize=FIGSIZE)
ax.grid(True, which="major", color=GRIGLIA, lw=1)
ax.axhline(63 / 256, color=GRIGIO, ls="--", lw=2)
ax.text(1.2e-4, 63 / 256 + 0.012, "caso: 63/256 ≈ 0,246", color=GRIGIO, fontsize=20)
ax.axhline(0.75, color=GRIGIO, ls=":", lw=2)
ax.text(1.2e-4, 0.762, "ideale 3/4  (con p$_g$ = 0: 0,749)", color=GRIGIO, fontsize=20)
ax.plot(pg, ps, color=BLU, lw=3, marker="o", ms=10, mec="white", mew=2)
cerchio(ax, 1e-2, 0.5651)
for x, y, t, dx, dy in [(1e-2, 0.5651, "0,565", 16, 6),
                        (2e-2, 0.4518, "0,452", 14, 4),
                        (5e-2, 0.2953, "0,295", 12, 8)]:
    ax.annotate(t, (x, y), xytext=(dx, dy), textcoords="offset points",
                fontsize=21, color=TESTO, fontweight="bold")
ax.set_xscale("log")
ax.set_xlim(7e-5, 7e-1)
ax.set_ylim(0.2, 0.8)
ax.set_xticks([1e-4, 1e-3, 1e-2, 1e-1])
ax.set_xticklabels(["0,01%", "0,1%", "1%", "10%"])
ax.xaxis.set_minor_formatter(mt.NullFormatter())
ax.yaxis.set_major_formatter(virgola(".1f"))
ax.set_xlabel("Errore per porta $p_g$ (scala logaritmica)")
ax.set_ylabel("Successo per singola misura")
salva(fig, "v2_s13_shor_successo_vs_pg.png")

# --- Slide 14: iterazioni al primo successo (Tab. 5.3) -------------------------
strategie = ["TOP-1", "TOP-4", "Metodo 2\n(ML + TOP-4)"]
uc1, uc2 = [1.37, 1.00, 1.50], [1.50, 1.00, 1.37]
fig, ax = plt.subplots(figsize=FIGSIZE)
ax.grid(True, axis="y", color=GRIGLIA, lw=1)
ax.set_axisbelow(True)
w = 0.36
xs = range(len(strategie))
for off, vals, col, lab in [(-w / 2, uc1, BLU, "UC1 (riferimento)"),
                            (w / 2, uc2, ARANCIO, "UC2 (stress)")]:
    bars = ax.bar([x + off for x in xs], vals, w - 0.03, color=col, label=lab)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.03,
                format(v, ".2f").replace(".", ","), ha="center",
                fontsize=22, fontweight="bold", color=TESTO)
ax.add_patch(FancyBboxPatch((1 - w - 0.06, 0.02), 2 * w + 0.12, 1.22,
                            boxstyle="round,pad=0,rounding_size=0.08",
                            fill=False, ec=ARANCIO, lw=3, zorder=5))
ax.set_xticks(list(xs))
ax.set_xticklabels(strategie)
ax.set_ylim(0, 1.75)
ax.set_yticks([0, 0.5, 1.0, 1.5])
ax.yaxis.set_major_formatter(virgola(".1f"))
ax.set_ylabel("Tentativi medi al primo successo\n(più basso = meglio)")
ax.legend(loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.13))
salva(fig, "v2_s14_iterazioni_primo_successo.png")

# --- Slide 15: soglia del surface code, base Z (JSON M7, fit Tab. 5.9) ---------
dati = json.loads((M7 / "results_M7_surface_z_20260808_001903.json")
                  .read_text(encoding="utf-8"))["curve"]["table"]
PTH = 0.0086
fig, ax = plt.subplots(figsize=FIGSIZE)
ax.axvspan(1.8e-3, PTH, color="#E8F3EA", zorder=0)
ax.axvspan(PTH, 1.1e-2, color="#FBE9E7", zorder=0)
ax.grid(True, which="major", color=GRIGLIA, lw=1)
ax.axvline(PTH, color=GRIGIO, ls="--", lw=2)
ax.text(PTH * 0.97, 1.5e-4, "soglia\n0,86%", color=GRIGIO, fontsize=20,
        ha="right", fontweight="bold")
ax.text(2.8e-3, 1.4e-5, "sotto soglia: d più grande = meno errori", color="#2E7D32",
        fontsize=18, fontweight="bold")
ax.text(1.08e-2, 3e-4, "sopra", color="#C62828", fontsize=19, fontweight="bold",
        ha="right")
toni = {"3": "#9DC3E6", "5": "#5B9BD5", "7": "#2E75B6", "9": SCURO}
for d, col in toni.items():
    xs_ = [r["p"] for r in dati[d]]
    ys_ = [r["p_L"] for r in dati[d]]
    ax.plot(xs_, ys_, color=col, lw=3, marker="o", ms=9, mec="white", mew=1.5,
            label=f"d = {d}")
cerchio(ax, 0.0087, 0.029, s=1300)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlim(1.8e-3, 1.1e-2)
ax.set_ylim(1e-5, 1e-1)
ax.set_xticks([2e-3, 3e-3, 5e-3, 1e-2])
ax.set_xticklabels(["0,2%", "0,3%", "0,5%", "1%"])
ax.xaxis.set_minor_formatter(mt.NullFormatter())
ax.set_xlabel("Errore fisico p (circuit-level)")
ax.set_ylabel("Errore logico $p_L$")
ax.legend(loc="upper left", frameon=True, facecolor="white", edgecolor=GRIGLIA,
          title="distanza", title_fontsize=19, ncol=2)
salva(fig, "v2_s15_surface_code_soglia_z.png")

# --- Slide 16: BP+OSD e ibrido contro MWPM (Tab. 5.15) ------------------------
ct = [0, 0.005, 0.010, 0.020, 0.040]
serie = [
    ("BP+OSD, d = 3", [1.146, 0.972, 0.980, 0.986, 0.999], GRIGIO_CHIARO, "-", "o"),
    ("BP+OSD, d = 5", [1.339, 1.270, 1.176, 1.094, 1.021], GRIGIO_CHIARO, "--", "s"),
    ("Ibrido, d = 3", [0.993, 1.185, 1.202, 1.213, 1.189], ARANCIO, "-", "o"),
    ("Ibrido, d = 5", [1.000, 1.011, 1.033, 1.029, 1.005], ARANCIO, "--", "s"),
]
fig, ax = plt.subplots(figsize=FIGSIZE)
ax.grid(True, color=GRIGLIA, lw=1)
ax.axhline(1.0, color=GRIGIO, lw=2)
ax.text(0.0405, 0.955, "MWPM = 1  (sopra: meglio di MWPM)", color=GRIGIO,
        fontsize=20, ha="right")
for lab, ys, col, ls, mk in serie:
    ax.plot(ct, ys, color=col, ls=ls, lw=3, marker=mk, ms=10,
            mec="white", mew=2, label=lab)
cerchio(ax, 0.010, 1.202)
ax.text(0.0112, 1.245, "1,20× = −16,8% di errori", fontsize=20,
        fontweight="bold", color=ARANCIO)
ax.set_xticks(ct)
ax.set_xticklabels(["0", "0,005", "0,01", "0,02", "0,04"])
ax.yaxis.set_major_formatter(virgola(".2f"))
ax.set_xlim(-0.002, 0.042)
ax.set_ylim(0.93, 1.37)
ax.set_xlabel("Intensità del crosstalk simulato")
ax.set_ylabel("Guadagno $p_L^{MWPM}\\,/\\,p_L$")
ax.legend(loc="upper right", ncol=2, frameon=False, bbox_to_anchor=(1.0, 1.02))
salva(fig, "v2_s16_decoder_bposd_ibrido.png")

# --- Slide 18: AQFT su N = 15 (Tab. 5.22) -------------------------------------
k = [1, 2, 3, 4, 5, 6, 7]
p = [0.6279, 0.5422, 0.5210, 0.4771, 0.4607, 0.4749, 0.4792]
fig, ax = plt.subplots(figsize=FIGSIZE)
ax.grid(True, color=GRIGLIA, lw=1)
ax.axhline(0.4792, color=GRIGIO, ls="--", lw=2)
ax.text(6.95, 0.487, "QFT piena (k = 7): 0,479", color=GRIGIO, fontsize=20, ha="right")
ax.plot(k, p, color=BLU, lw=3, marker="o", ms=11, mec="white", mew=2)
cerchio(ax, 1, 0.6279)
ax.annotate("k = 1 scelto in selezione\nverifica: 0,628", (1, 0.6279),
            xytext=(40, -12), textcoords="offset points", fontsize=21, va="center",
            color=TESTO, fontweight="bold")
ax.set_xticks(k)
ax.set_xlim(0.6, 7.3)
ax.set_ylim(0.44, 0.65)
ax.yaxis.set_major_formatter(virgola(".2f"))
ax.set_xlabel("Grado di troncamento $k_{QPE}$  (7 = QFT piena)")
ax.set_ylabel("Successo sui dati di verifica")
salva(fig, "v2_s18_aqft_n15_holdout.png")
print("ok")
