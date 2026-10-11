"""Render the M8 logical-noise curve from explicit schema-v2 inputs.

The QEC regimes are annotations supplied by the caller. This consumer never
infers a direct M6/M7-to-p_L conversion: M8's p_L is only the phenomenological
per-gate Pauli proxy declared in the result manifest.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


M8_RESULT_REVISION = "m8-logical-pauli-proxy-v2-replicated"
M8_NOISE_REVISION = "phenomenological-pauli-per-gate-v2"


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: la radice JSON deve essere un oggetto.")
    return data


def load_m8_results(path: Path) -> tuple[dict, list[dict]]:
    data = _read_json(path)
    if data.get("schema_version") != "2.0" or data.get("milestone") != "M8_shor_logico":
        raise ValueError("L'input deve essere un risultato M8 con schema_version=2.0.")
    if data.get("revision") != M8_RESULT_REVISION:
        raise ValueError(
            f"L'input M8 deve avere revision={M8_RESULT_REVISION!r}; "
            "un vecchio JSON schema 2.0 non e' compatibile."
        )
    manifest = data.get("logical_noise_manifest", {})
    if (
        manifest.get("revision") != M8_NOISE_REVISION
        or manifest.get("kind") != "phenomenological_per_gate_proxy"
        or manifest.get("direct_equivalence_to_M6_M7") is not False
    ):
        raise ValueError("Manca il manifest del proxy fenomenologico per gate.")
    circuit_manifest = data.get("circuit_manifest")
    if not isinstance(circuit_manifest, dict):
        raise ValueError("Manca circuit_manifest nel risultato M8.")
    required_manifest = (
        "circuit_revision",
        "postprocess_revision",
        "circuit_sha256",
        "basis_gates",
        "seed_transpiler",
        "gate_counts",
    )
    missing = [key for key in required_manifest if key not in circuit_manifest]
    if missing:
        raise ValueError(f"circuit_manifest M8 incompleto: {', '.join(missing)}.")
    digest = circuit_manifest.get("circuit_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("circuit_manifest.circuit_sha256 non valido.")

    config = data.get("config")
    if not isinstance(config, dict):
        raise ValueError("Manca config nel risultato M8.")
    if (config.get("N"), config.get("a"), config.get("n_count")) != (15, 7, 8):
        raise ValueError("Il consumer ufficiale accetta soltanto M8 per N=15, a=7, n_count=8.")
    for key in ("seed", "replicate_count", "shots_per_replicate", "confidence"):
        if key not in config:
            raise ValueError(f"config M8 privo di {key}.")
    points = data.get("curve", {}).get("points")
    if not isinstance(points, list) or len(points) < 2:
        raise ValueError("La curva M8 deve contenere almeno due punti.")

    previous = -1.0
    zero_count = 0
    for point in points:
        try:
            p_L = float(point["p_L"])
            estimate = float(point["P_success"])
            low = float(point["wilson_ci"]["low"])
            high = float(point["wilson_ci"]["high"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Punto M8 privo di p_L, P_success o Wilson CI validi.") from error
        if not all(math.isfinite(value) for value in (p_L, estimate, low, high)):
            raise ValueError("La curva M8 contiene valori non finiti.")
        if not (0.0 <= p_L <= 1.0 and 0.0 <= low <= estimate <= high <= 1.0):
            raise ValueError("Dominio o Wilson CI non valido in un punto M8.")
        if p_L <= previous:
            raise ValueError("La griglia p_L M8 deve essere strettamente crescente.")
        previous = p_L
        zero_count += int(p_L == 0.0)
    if float(points[0]["p_L"]) != 0.0 or zero_count != 1:
        raise ValueError("La griglia M8 deve iniziare con un unico p_L=0.")
    point_grid = [float(point["p_L"]) for point in points]
    config_grid = config.get("p_grid")
    curve_grid = data.get("curve", {}).get("p_grid")
    if config_grid != point_grid or curve_grid != point_grid:
        raise ValueError("config.p_grid, curve.p_grid e punti M8 non coincidono.")
    if float(data.get("curve", {}).get("P_ideal", -1.0)) != float(points[0]["P_success"]):
        raise ValueError("curve.P_ideal non coincide con il punto p_L=0.")
    return data, points


def load_regimes(path: Path, minimum: float, maximum: float) -> list[dict]:
    data = _read_json(path)
    if data.get("schema_version") != "2.0" or not isinstance(data.get("regimes"), list):
        raise ValueError("Il file regimi deve avere schema_version=2.0 e una lista regimes.")
    regimes = []
    seen_labels: set[str] = set()
    for raw in data["regimes"]:
        if not isinstance(raw, dict):
            raise ValueError("Ogni regime deve essere un oggetto JSON.")
        label = raw.get("label")
        source = raw.get("source")
        try:
            p_L = float(raw["p_L"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Ogni regime richiede un p_L numerico.") from error
        normalized_label = label.strip() if isinstance(label, str) else ""
        if not normalized_label or normalized_label in seen_labels:
            raise ValueError("Le etichette dei regimi devono essere stringhe uniche non vuote.")
        if not isinstance(source, str) or not source.strip():
            raise ValueError(f"Il regime {label!r} richiede una fonte/motivazione esplicita.")
        if not math.isfinite(p_L) or not minimum <= p_L <= maximum:
            raise ValueError(
                f"Il p_L del regime {label!r} deve cadere nell'intervallo simulato "
                f"[{minimum:g}, {maximum:g}]; non si esegue estrapolazione."
            )
        regimes.append(
            {"label": normalized_label, "p_L": p_L, "source": source.strip()}
        )
        seen_labels.add(normalized_label)
    if not regimes:
        raise ValueError("Il file regimi deve contenere almeno un regime.")
    return regimes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Figura M8 da input schema-v2 esplicito")
    parser.add_argument("--input", type=Path, required=True, help="JSON M8 schema v2")
    parser.add_argument(
        "--regimes",
        type=Path,
        help=("JSON schema v2 opzionale con label, p_L e fonte. Ometterlo per "
              "non suggerire conversioni dirette da M6/M7."),
    )
    parser.add_argument(
        "--output-base",
        type=Path,
        required=True,
        help="Percorso esplicito senza estensione; produce .pdf e .png",
    )
    return parser


def main(argv=None) -> tuple[Path, Path]:
    args = build_parser().parse_args(argv)
    _, points = load_m8_results(args.input)
    p_L = np.asarray([float(point["p_L"]) for point in points])
    estimates = np.asarray([float(point["P_success"]) for point in points])
    lows = np.asarray([float(point["wilson_ci"]["low"]) for point in points])
    highs = np.asarray([float(point["wilson_ci"]["high"]) for point in points])
    positive = p_L > 0.0
    if positive.sum() < 2:
        raise ValueError("Servono almeno due p_L positivi per la figura logaritmica.")
    regimes = (
        load_regimes(args.regimes, float(p_L[positive].min()), float(p_L.max()))
        if args.regimes is not None else []
    )

    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    ideal = estimates[0]
    ax.axhline(
        ideal,
        color="0.55",
        linestyle=":",
        linewidth=1.0,
        label=f"stima a $p_L=0$ ({ideal:.3f})",
    )
    y_error = np.vstack(
        (estimates[positive] - lows[positive], highs[positive] - estimates[positive])
    )
    ax.errorbar(
        p_L[positive],
        estimates[positive],
        yerr=y_error,
        fmt="o-",
        color="C0",
        markersize=4,
        linewidth=1.4,
        capsize=2,
        label="Shor $N=15$ (Wilson CI)",
    )

    log_grid = np.log10(p_L[positive])
    for index, regime in enumerate(regimes, start=1):
        x_value = regime["p_L"]
        y_value = float(np.interp(np.log10(x_value), log_grid, estimates[positive]))
        color = f"C{index % 10}"
        ax.axvline(x_value, color=color, linestyle="--", linewidth=1.0, alpha=0.75)
        ax.plot(x_value, y_value, "D", color=color, markersize=6, label=regime["label"])

    ax.set_xscale("log")
    ax.set_xlim(float(p_L[positive].min()) * 0.8, float(p_L.max()) * 1.25)
    visible_low = min(float(lows.min()), ideal)
    visible_high = max(float(highs.max()), ideal)
    padding = max(0.04, (visible_high - visible_low) * 0.15)
    ax.set_ylim(max(0.0, visible_low - padding), min(1.0, visible_high + padding))
    ax.set_xlabel(r"proxy di errore logico per gate $p_L$")
    ax.set_ylabel("probabilita' di successo di Shor")
    ax.set_title("Shor sotto il proxy fenomenologico di errore logico")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, which="both")
    footer = (
        "I regimi sono input esterni: p_L non e' una conversione diretta delle metriche M6/M7."
        if regimes else
        "p_L e' un proxy fenomenologico per gate; non e' convertito dalle metriche M6/M7."
    )
    fig.text(0.5, 0.005, footer, ha="center", fontsize=7, color="0.35")
    fig.tight_layout(rect=(0, 0.035, 1, 1))

    args.output_base.parent.mkdir(parents=True, exist_ok=True)
    pdf = args.output_base.with_suffix(".pdf")
    png = args.output_base.with_suffix(".png")
    fig.savefig(pdf)
    fig.savefig(png, dpi=150)
    plt.close(fig)
    print(f"Figura salvata: {pdf} / {png}")
    for regime in regimes:
        print(f"  {regime['label']}: p_L={regime['p_L']:g}; fonte={regime['source']}")
    return pdf, png


if __name__ == "__main__":
    main()
