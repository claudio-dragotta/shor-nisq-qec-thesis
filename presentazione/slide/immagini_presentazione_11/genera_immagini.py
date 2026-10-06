"""Prepara le immagini della presentazione da 11 slide.

Copia le figure della tesi (file_latex_v2/figure) e ridisegna i quattro grafici
usati in slide con virgola decimale, Arial e corpo leggibile su tela 1920x1080.
Ogni valore viene dalle tabelle del Capitolo 5 di file_latex_v2: nessun dato nuovo.

    python genera_immagini.py
"""
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mt
from PIL import Image

QUI = Path(__file__).resolve().parent
FIG = QUI.parents[2] / "file_latex_v2" / "figure"

BLU = "#125C97"      # titolo e serie primaria
ARANCIO = "#D9822B"  # seconda serie (validata CVD contro BLU)
SCURO = "#0B2F5B"
GRIGIO = "#5B6573"
GRIGLIA = "#E3E8EE"

plt.rcParams.update({
    "font.family": "Arial", "font.size": 22, "axes.labelsize": 24,
    "xtick.labelsize": 22, "ytick.labelsize": 22, "legend.fontsize": 21,
    "axes.edgecolor": GRIGIO, "axes.labelcolor": "#1F2933",
    "xtick.color": "#1F2933", "ytick.color": "#1F2933",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.formatter.use_locale": False,
})


def virgola(fmt):
    return mt.FuncFormatter(lambda v, _: format(v, fmt).replace(".", ","))


def salva(fig, nome):
    fig.savefig(QUI / nome, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def copia(src, dst):
    shutil.copy2(FIG / src, QUI / dst)


# --- Slide 1: sfera di Bloch ritagliata, sfondo trasparente -------------------
im = Image.open(FIG / "bloch_sphere.png").convert("RGBA")
px = im.load()
for y in range(im.height):
    for x in range(im.width):
        r, g, b, a = px[x, y]
        if r > 250 and g > 250 and b > 250:
            px[x, y] = (255, 255, 255, 0)
im.crop(im.getbbox()).save(QUI / "s01_copertina_sfera_bloch.png")
Image.open(FIG / "ucbm-logo.png").convert("RGBA").save(QUI / "logo_ucbm.png")

# --- Slide 3: successo di Shor contro p_g (Tab. 5.19) ------------------------
pg = [1e-4, 5e-4, 1e-3, 1.7e-3, 2e-3, 5e-3, 1e-2, 2e-2, 5e-2, 1e-1, 2e-1, 5e-1]
ps = [0.7469, 0.7373, 0.7250, 0.7083, 0.6992, 0.6450, 0.5651, 0.4518,
      0.2953, 0.2503, 0.2441, 0.2459]
fig, ax = plt.subplots(figsize=(11, 6.2))
ax.grid(True, which="major", color=GRIGLIA, lw=1)
ax.axhline(63 / 256, color=GRIGIO, ls="--", lw=2)
ax.text(1.2e-4, 63 / 256 + 0.012, "pavimento uniforme 63/256 ≈ 0,246",
        color=GRIGIO, fontsize=20)
ax.axhline(0.75, color=GRIGIO, ls=":", lw=2)
ax.text(1.2e-4, 0.762, "ideale 3/4", color=GRIGIO, fontsize=20)
ax.plot(pg, ps, color=BLU, lw=3, marker="o", ms=10, mec="white", mew=2)
for x, y, t, dx, dy in [(1e-2, 0.5651, "0,565", 10, 8),
                        (5e-2, 0.2953, "0,295", 12, 6)]:
    ax.annotate(t, (x, y), xytext=(dx, dy), textcoords="offset points",
                fontsize=21, color="#1F2933", fontweight="bold")
ax.set_xscale("log")
ax.set_xlim(7e-5, 7e-1)
ax.set_ylim(0.2, 0.8)
ax.set_xticks([1e-4, 1e-3, 1e-2, 1e-1])
ax.set_xticklabels(["0,0001", "0,001", "0,01", "0,1"])
ax.yaxis.set_major_formatter(virgola(".1f"))
ax.set_xlabel("Proxy di errore Pauli per gate $p_g$ (scala log)")
ax.set_ylabel("Probabilità di fattorizzazione\nper singola misura")
salva(fig, "s03_shor_successo_vs_pg.png")

# --- Slide 9: iterazioni al primo successo (Tab. 5.3) -------------------------
strategie = ["TOP-1", "TOP-4", "M2\n(ML + TOP-4)"]
uc1, uc2 = [1.37, 1.00, 1.50], [1.50, 1.00, 1.37]
fig, ax = plt.subplots(figsize=(11, 6.2))
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
                fontsize=22, fontweight="bold", color="#1F2933")
ax.set_xticks(list(xs))
ax.set_xticklabels(strategie)
ax.set_ylim(0, 1.75)
ax.set_yticks([0, 0.5, 1.0, 1.5])
ax.yaxis.set_major_formatter(virgola(".1f"))
ax.set_ylabel("Iterazioni medie al primo successo")
ax.legend(loc="upper center", ncol=2, frameon=False,
          bbox_to_anchor=(0.5, 1.13))
salva(fig, "s09_iterazioni_primo_successo.png")

# --- Slide 10: BP+OSD e ibrido contro MWPM (Tab. 5.15) ------------------------
ct = [0, 0.005, 0.010, 0.020, 0.040]
serie = [
    ("BP+OSD, d = 3", [1.146, 0.972, 0.980, 0.986, 0.999], BLU, "-", "o"),
    ("BP+OSD, d = 5", [1.339, 1.270, 1.176, 1.094, 1.021], BLU, "--", "s"),
    ("Ibrido, d = 3", [0.993, 1.185, 1.202, 1.213, 1.189], ARANCIO, "-", "o"),
    ("Ibrido, d = 5", [1.000, 1.011, 1.033, 1.029, 1.005], ARANCIO, "--", "s"),
]
fig, ax = plt.subplots(figsize=(11, 6.2))
ax.grid(True, color=GRIGLIA, lw=1)
ax.axhline(1.0, color=GRIGIO, lw=2)
ax.text(0.0405, 0.955, "MWPM = 1  (sopra: meglio di MWPM)", color=GRIGIO,
        fontsize=20, ha="right")
for lab, ys, col, ls, mk in serie:
    ax.plot(ct, ys, color=col, ls=ls, lw=3, marker=mk, ms=10,
            mec="white", mew=2, label=lab)
ax.set_xticks(ct)
ax.set_xticklabels(["0", "0,005", "0,01", "0,02", "0,04"])
ax.yaxis.set_major_formatter(virgola(".2f"))
ax.set_xlim(-0.002, 0.042)
ax.set_ylim(0.93, 1.37)
ax.set_xlabel("Intensità del crosstalk simulato")
ax.set_ylabel("Guadagno $p_L^{MWPM}\\,/\\,p_L$")
ax.legend(loc="upper right", ncol=2, frameon=False)
salva(fig, "s10_decoder_bposd_ibrido.png")

# --- Riserva DR5: AQFT su N = 15 (Tab. 5.22) ----------------------------------
k = [1, 2, 3, 4, 5, 6, 7]
p = [0.6279, 0.5422, 0.5210, 0.4771, 0.4607, 0.4749, 0.4792]
fig, ax = plt.subplots(figsize=(11, 6.2))
ax.grid(True, color=GRIGLIA, lw=1)
ax.axhline(0.4792, color=GRIGIO, ls="--", lw=2)
ax.text(6.95, 0.487, "QFT piena (k = 7): 0,479", color=GRIGIO,
        fontsize=20, ha="right")
ax.plot(k, p, color=BLU, lw=3, marker="o", ms=11, mec="white", mew=2)
ax.annotate("k = 1 scelto in selezione\nholdout 0,628", (1, 0.6279),
            xytext=(40, -12), textcoords="offset points", fontsize=21, va="center",
            color="#1F2933", fontweight="bold")
ax.set_xticks(k)
ax.set_ylim(0.44, 0.65)
ax.yaxis.set_major_formatter(virgola(".2f"))
ax.set_xlabel("Grado di troncamento $k_{QPE}$")
ax.set_ylabel("Successo su holdout")
salva(fig, "r_aqft_n15_holdout.png")

# --- Copie delle figure originali della tesi ---------------------------------
for src, dst in [
    ("finale_fig_3_2_pipeline_shor.png", "orig_3_2_pipeline_shor.png"),
    ("finale_fig_3_3_sorgenti_rumore.png", "orig_3_3_sorgenti_rumore.png"),
    ("finale_fig_3_5_disegno_sperimentale.png", "orig_3_5_disegno_sperimentale.png"),
    ("finale_fig_4_1_architettura_piattaforma.png", "orig_4_1_architettura_piattaforma.png"),
    ("finale_fig_4_2_pipeline_appaiata.png", "orig_4_2_pipeline_appaiata.png"),
    ("finale_fig_4_3_flusso_decoder.png", "orig_4_3_flusso_decoder.png"),
    ("finale_fig_5_1_iterazioni_primo_successo.png", "orig_5_1_iterazioni.png"),
    ("finale_fig_5_4_surface_code_soglia.png", "r_surface_code_soglia_orig_5_4.png"),
    ("finale_fig_5_6_decoder_bposd_ibrido.png", "orig_5_6_decoder_bposd_ibrido.png"),
    ("finale_fig_5_7_shor_successo_proxy_gate.png", "orig_5_7_shor_successo_pg.png"),
    ("finale_fig_5_9_aqft_n15_holdout.png", "orig_5_9_aqft_n15.png"),
    ("finale_fig_5_10_aqft_qpe_holdout.png", "r_aqft_qpe_holdout_orig_5_10.png"),
]:
    copia(src, dst)

print("Immagini scritte in", QUI)
