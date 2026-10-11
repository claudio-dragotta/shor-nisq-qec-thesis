"""Plot cumulative Shor success using only explicitly selected M8-v2 points."""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from gen_shor_logico import load_m8_results


def select_points(points: list[dict], requested: list[float]) -> list[dict]:
    if not requested:
        raise ValueError("Specificare almeno un p_L con --p-values.")
    selected = []
    seen: set[float] = set()
    for value in requested:
        p_value = float(value)
        if not math.isfinite(p_value) or not 0.0 <= p_value <= 1.0:
            raise ValueError("Ogni --p-values deve appartenere a [0, 1].")
        if p_value in seen:
            raise ValueError("--p-values non puo' contenere duplicati.")
        matches = [
            point
            for point in points
            if math.isclose(float(point["p_L"]), p_value, rel_tol=0.0, abs_tol=1e-15)
        ]
        if len(matches) != 1:
            available = ", ".join(f"{float(point['p_L']):g}" for point in points)
            raise ValueError(
                f"p_L={p_value:g} non e' un punto M8 esatto. Valori disponibili: {available}."
            )
        selected.append(matches[0])
        seen.add(p_value)
    return selected


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Successo cumulativo da punti M8 espliciti")
    parser.add_argument("--input", type=Path, required=True, help="JSON M8 schema v2")
    parser.add_argument(
        "--p-values",
        type=float,
        nargs="+",
        required=True,
        help="Punti p_L esatti da includere, senza fallback o nearest-neighbour",
    )
    parser.add_argument("--max-runs", type=int, default=8)
    parser.add_argument("--threshold", type=float, default=0.80)
    parser.add_argument(
        "--output-base",
        type=Path,
        required=True,
        help="Percorso esplicito senza estensione; produce .pdf e .png",
    )
    return parser


def main(argv=None) -> tuple[Path, Path]:
    args = build_parser().parse_args(argv)
    if type(args.max_runs) is not int or args.max_runs < 1:
        raise SystemExit("Configurazione non valida: max-runs deve essere positivo.")
    if not 0.0 < args.threshold < 1.0:
        raise SystemExit("Configurazione non valida: threshold deve appartenere a (0, 1).")
    _, points = load_m8_results(args.input)
    selected = select_points(points, args.p_values)
    runs = np.arange(1, args.max_runs + 1)

    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    ax.axhline(
        args.threshold,
        color="0.35",
        linestyle=":",
        linewidth=1.3,
        label=f"soglia {args.threshold:.0%}",
    )
    summaries = []
    markers = ("o", "s", "^", "D", "v", "P", "X")
    for index, point in enumerate(selected):
        probability = float(point["P_success"])
        low = float(point["wilson_ci"]["low"])
        high = float(point["wilson_ci"]["high"])
        cumulative = 1.0 - (1.0 - probability) ** runs
        cumulative_low = 1.0 - (1.0 - low) ** runs
        cumulative_high = 1.0 - (1.0 - high) ** runs
        color = f"C{index % 10}"
        label = f"$p_L={float(point['p_L']):g}$; $P_s={probability:.3f}$"
        ax.plot(
            runs,
            cumulative,
            marker=markers[index % len(markers)],
            color=color,
            markersize=5,
            linewidth=1.4,
            label=label,
        )
        ax.fill_between(runs, cumulative_low, cumulative_high, color=color, alpha=0.12)
        crossing = np.flatnonzero(cumulative >= args.threshold)
        first_crossing = int(runs[crossing[0]]) if crossing.size else None
        if first_crossing is not None:
            crossing_value = float(cumulative[first_crossing - 1])
            ax.plot(
                first_crossing,
                crossing_value,
                "o",
                color=color,
                markersize=10,
                markerfacecolor="none",
                markeredgewidth=1.5,
            )
        summaries.append((float(point["p_L"]), probability, first_crossing))

    ax.set_xlabel(r"numero di esecuzioni indipendenti $k$")
    ax.set_ylabel(r"$P(k)=1-(1-P_s)^k$")
    ax.set_title("Probabilita' cumulativa dai punti M8 selezionati")
    ax.set_xticks(runs)
    ax.set_ylim(0.0, 1.02)
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(alpha=0.3)
    fig.tight_layout()

    args.output_base.parent.mkdir(parents=True, exist_ok=True)
    pdf = args.output_base.with_suffix(".pdf")
    png = args.output_base.with_suffix(".png")
    fig.savefig(pdf)
    fig.savefig(png, dpi=150)
    plt.close(fig)
    for p_L, probability, crossing in summaries:
        crossing_text = str(crossing) if crossing is not None else f">{args.max_runs}"
        print(
            f"  p_L={p_L:g}, Ps={probability:.4f}: k soglia {args.threshold:.0%} = "
            f"{crossing_text}"
        )
    print(f"Figura salvata: {pdf} / {png}")
    return pdf, png


if __name__ == "__main__":
    main()
