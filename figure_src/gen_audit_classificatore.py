"""Genera le figure dell'audit classificatore esclusivamente da artefatti JSON v2.

Non cerca file ``latest``, non incorpora misure storiche e non avvia Aer. Sono richiesti
esplicitamente il diagnostico della moda UC1, quello della frazione efficace e il manifest
del training v2. Artefatti mancanti, storici o riferiti a circuiti incompatibili causano un
errore esplicito.
"""

from __future__ import annotations

import argparse
import json
from math import comb
from pathlib import Path
from typing import Any, Mapping

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


SCHEMA_VERSION = "2.0"
MODE_ARTIFACT = "phase1-mode-zero-uc1"
FRACTION_ARTIFACT = "phase1-effective-signal-fraction"
MANIFEST_KEYS = (
    "circuit_revision",
    "noise_model_revision",
    "postprocess_revision",
    "circuit_sha256",
    "basis_gates",
    "optimization_level",
    "seed_transpiler",
)


class ArtifactError(ValueError):
    """Errore di contratto o provenienza di un input scientifico."""


def _mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ArtifactError(f"{context} deve essere un oggetto JSON.")
    return value


def load_v2_json(
    path: Path, *, label: str, expected_artifact_type: str | None = None
) -> dict:
    path = Path(path)
    if not path.is_file():
        raise ArtifactError(f"Artefatto {label} mancante o non leggibile: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ArtifactError(f"JSON non valido per {label} ({path}): {exc}") from exc
    payload = dict(_mapping(payload, f"payload {label}"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        shown = payload.get("schema_version", "assente")
        raise ArtifactError(
            f"{path}: schema_version={shown!r}; richiesto esclusivamente '2.0'."
        )
    if expected_artifact_type is not None:
        observed = payload.get("artifact_type")
        if observed != expected_artifact_type:
            raise ArtifactError(
                f"{path}: artifact_type={observed!r}; atteso {expected_artifact_type!r}."
            )
    manifest = _mapping(payload.get("manifest"), f"manifest in {path}")
    missing = [key for key in MANIFEST_KEYS if key not in manifest]
    if missing:
        raise ArtifactError(
            f"{path}: manifest v2 incompleto; mancano {', '.join(missing)}."
        )
    return payload


def manifest_signature(payload: Mapping[str, Any]) -> dict:
    manifest = _mapping(payload.get("manifest"), "manifest")
    return {key: manifest[key] for key in MANIFEST_KEYS}


def validate_compatible_manifests(inputs: Mapping[str, Mapping[str, Any]]) -> dict:
    signatures = {label: manifest_signature(payload) for label, payload in inputs.items()}
    first_label, reference = next(iter(signatures.items()))
    for label, signature in signatures.items():
        differences = [
            key for key in MANIFEST_KEYS if signature[key] != reference[key]
        ]
        if differences:
            raise ArtifactError(
                f"Manifest incompatibili fra {first_label} e {label}: "
                f"{', '.join(differences)}."
            )
    return reference


def load_inputs(mode_json: Path, fraction_json: Path, training_json: Path) -> tuple[dict, dict, dict, dict]:
    mode = load_v2_json(
        mode_json, label="diagnostico moda", expected_artifact_type=MODE_ARTIFACT
    )
    fraction = load_v2_json(
        fraction_json,
        label="diagnostico frazione efficace",
        expected_artifact_type=FRACTION_ARTIFACT,
    )
    training = load_v2_json(training_json, label="manifest training")
    if not isinstance(training.get("outcomes"), Mapping):
        raise ArtifactError(
            f"{training_json}: manca l'oggetto outcomes del training v2."
        )
    signature = validate_compatible_manifests(
        {"moda": mode, "frazione": fraction, "training": training}
    )
    return mode, fraction, training, signature


def _save(fig: plt.Figure, output_dir: Path, name: str) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf = output_dir / f"{name}.pdf"
    png = output_dir / f"{name}.png"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {pdf}")
    return [pdf, png]


def fig_istogramma_moda_zero(mode: Mapping[str, Any], output_dir: Path) -> list[Path]:
    representative = mode.get("representative_mode_zero")
    if not isinstance(representative, Mapping):
        raise ArtifactError(
            "Il diagnostico della moda non contiene una replica con moda y=0. "
            "Aumentare --reps e rigenerare esplicitamente l'artefatto."
        )
    config = _mapping(mode.get("config"), "config diagnostico moda")
    reference = _mapping(mode.get("reference"), "reference diagnostico moda")
    n_count = int(config.get("n_count", 0))
    n_cells = 2**n_count
    counts = np.asarray(representative.get("histogram_counts"), dtype=float)
    if counts.ndim != 1 or len(counts) != n_cells or np.any(counts < 0):
        raise ArtifactError(
            f"histogram_counts deve contenere {n_cells} conteggi non negativi."
        )
    total = float(counts.sum())
    if total <= 0:
        raise ArtifactError("L'istogramma rappresentativo non contiene shot.")
    probabilities = counts / total
    useful_peaks = [int(value) for value in reference.get("useful_theoretical_peaks", [])]
    if any(not 0 <= value < n_cells for value in useful_peaks):
        raise ArtifactError("Picchi teorici fuori dal dominio dell'istogramma.")

    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    x = np.arange(n_cells)
    ax.bar(x, probabilities, width=1.0, color="0.75", label="altri esiti")
    if useful_peaks:
        ax.bar(
            useful_peaks,
            probabilities[useful_peaks],
            width=3.0,
            color="C2",
            label="picchi teorici utili per i fattori",
        )
    ax.bar(
        [0],
        probabilities[[0]],
        width=3.0,
        color="C3",
        label="moda y=0: fase nulla, scartata",
    )

    top_rows = representative.get("ordered_top4")
    if not isinstance(top_rows, list) or not top_rows:
        raise ArtifactError("La replica rappresentativa non contiene ordered_top4.")
    y_offset = max(float(probabilities.max()) * 0.08, 0.002)
    for row in top_rows:
        row = _mapping(row, "riga ordered_top4")
        value = int(row["value"])
        rank = int(row["rank"])
        ax.annotate(
            f"#{rank}\n$y={value}$",
            xy=(value, probabilities[value]),
            xytext=(value, probabilities[value] + y_offset),
            ha="center",
            fontsize=8.5,
            color="C3" if value == 0 else ("C2" if row.get("factor_success") else "0.3"),
            fontweight="bold",
        )

    ax.set_xlabel(f"esito della misura y ({n_cells} celle)")
    ax.set_ylabel("frequenza relativa")
    ax.set_title(
        f"Replica {representative.get('rep')} di {config.get('use_case')} con moda y=0 "
        f"(seed {representative.get('seed_simulator')})",
        fontsize=10.5,
    )
    ax.set_xlim(-4, n_cells + 3)
    ax.set_ylim(0, max(float(probabilities.max()) * 1.30, 0.01))
    ticks = sorted({0, *reference.get("theoretical_peaks", []), n_cells - 1})
    ax.set_xticks(ticks)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.17), frameon=False)
    ax.grid(alpha=0.25, axis="y")
    return _save(fig, output_dir, "audit_istogramma_negativo")


def _training_audits(training: Mapping[str, Any]) -> list[dict]:
    outcomes = _mapping(training.get("outcomes"), "outcomes training")
    audits = []
    for use_case, by_top_k in outcomes.items():
        by_top_k = _mapping(by_top_k, f"outcomes[{use_case!r}]")
        for top_k_key, value in by_top_k.items():
            audit = _mapping(value, f"audit {use_case}/TOP-{top_k_key}")
            if audit.get("schema_version") != SCHEMA_VERSION:
                raise ArtifactError(
                    f"Audit {use_case}/TOP-{top_k_key} non è schema v2."
                )
            validate_compatible_manifests(
                {"training": training, f"audit {use_case}/TOP-{top_k_key}": audit}
            )
            balance = _mapping(
                audit.get("class_balance"), f"class_balance {use_case}/TOP-{top_k_key}"
            )
            positive = int(balance.get("positive", -1))
            negative = int(balance.get("negative", -1))
            if positive < 0 or negative < 0 or positive + negative == 0:
                raise ArtifactError(
                    f"Bilanciamento non valido per {use_case}/TOP-{top_k_key}."
                )
            noise = _mapping(audit.get("noise_base"), f"noise_base {use_case}")
            audits.append(
                {
                    "use_case": str(use_case),
                    "top_k": int(audit.get("label_top_k", top_k_key)),
                    "positive": positive,
                    "negative": negative,
                    "negative_rate": negative / (positive + negative),
                    "lambda_2q": float(noise["eps_2q"]),
                }
            )
    if not audits:
        raise ArtifactError("Il training_manifest non contiene audit di etichettatura.")
    return audits


def fig_frazione_efficace(
    fraction: Mapping[str, Any], training: Mapping[str, Any], output_dir: Path
) -> list[Path]:
    results = fraction.get("results")
    if not isinstance(results, list) or not results:
        raise ArtifactError("Il diagnostico della frazione efficace non contiene risultati.")
    rows = sorted(
        (_mapping(row, "riga results frazione") for row in results),
        key=lambda row: float(row["lambda_2q"]),
    )
    lambdas = np.asarray([float(row["lambda_2q"]) for row in rows])
    effective = np.asarray([float(row["effective_signal_fraction"]) for row in rows])
    proxy = np.asarray([float(row["p_no_nonidentity_2q_proxy"]) for row in rows])
    if np.any(lambdas <= 0) or np.any(effective <= 0) or np.any(proxy <= 0):
        raise ArtifactError(
            "La figura logaritmica richiede lambda, frazione efficace e proxy positivi."
        )
    circuit = _mapping(fraction.get("circuit"), "circuit diagnostico frazione")
    n_cx = int(circuit["n_cx"])

    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    ax.plot(
        lambdas,
        proxy,
        "s--",
        color="C3",
        ms=5,
        lw=1.3,
        label=rf"proxy $(1-15\lambda_{{2q}}/16)^{{{n_cx}}}$",
    )
    ax.plot(
        lambdas,
        effective,
        "o-",
        color="C0",
        ms=6,
        lw=1.6,
        label="$f$ efficace del modello di miscela",
    )

    use_case_lambdas = {}
    for audit in _training_audits(training):
        use_case_lambdas.setdefault(audit["use_case"], audit["lambda_2q"])
    y_min = float(min(effective.min(), proxy.min()))
    y_max = float(max(effective.max(), proxy.max()))
    for use_case, value in sorted(use_case_lambdas.items()):
        if lambdas.min() <= value <= lambdas.max():
            ax.axvline(value, color="0.6", ls=":", lw=1)
            ax.annotate(
                use_case,
                xy=(value, y_min * 1.8),
                fontsize=8,
                color="0.35",
                ha="center",
                backgroundcolor="white",
            )

    last_ratio = effective[-1] / proxy[-1]
    ax.annotate(
        f"rapporto descrittivo\n$={last_ratio:.1e}$",
        xy=(lambdas[-1], np.sqrt(effective[-1] * proxy[-1])),
        xytext=(lambdas[-1] * 0.70, np.sqrt(effective[-1] * proxy[-1])),
        fontsize=8.5,
        ha="right",
        color="0.25",
    )
    ax.annotate(
        "",
        xy=(lambdas[-1], effective[-1]),
        xytext=(lambdas[-1], proxy[-1]),
        arrowprops={"arrowstyle": "<->", "color": "0.5", "lw": 1},
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylim(y_min * 0.5, y_max * 2)
    ax.set_xlabel(r"parametro depolarizzante Qiskit $\lambda_{2q}$")
    ax.set_ylabel("frazione efficace / proxy no-evento-2Q")
    ax.set_title("Segnale sui picchi e proxy indipendente no-evento-2Q", fontsize=11)
    ax.legend(fontsize=8, loc="best")
    ax.grid(alpha=0.3, which="both")
    return _save(fig, output_dir, "frazione_coerente")


def fig_tetto_classe_negativa(
    mode: Mapping[str, Any], training: Mapping[str, Any], output_dir: Path
) -> list[Path]:
    config = _mapping(mode.get("config"), "config diagnostico moda")
    reference = _mapping(mode.get("reference"), "reference diagnostico moda")
    n_cells = 2 ** int(config["n_count"])
    factorable = int(reference["factorable_outcome_count"])
    listed_factorable = reference.get("factorable_outcomes")
    if not isinstance(listed_factorable, list) or len(listed_factorable) != factorable:
        raise ArtifactError("Elenco degli outcome fattorizzanti incompleto o incoerente.")
    if not 0 < factorable < n_cells:
        raise ArtifactError("Numero di outcome fattorizzanti fuori dominio.")
    audits = _training_audits(training)
    max_k = max(row["top_k"] for row in audits)
    if not 1 <= max_k <= n_cells:
        raise ArtifactError("label_top_k fuori dominio nel training_manifest.")
    ks = np.arange(1, max_k + 1)
    nonfactorable = n_cells - factorable
    ceiling = np.asarray(
        [
            comb(nonfactorable, int(k)) / comb(n_cells, int(k))
            if k <= nonfactorable
            else 0.0
            for k in ks
        ]
    )

    fig, ax = plt.subplots(figsize=(6.6, 4.5))
    ax.plot(
        ks,
        100 * ceiling,
        "-",
        color="0.4",
        lw=1.6,
        label="tetto combinatorio su ranking uniforme senza reinserimento",
    )
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    for index, row in enumerate(sorted(audits, key=lambda item: (item["use_case"], item["top_k"]))):
        x = row["top_k"]
        y = 100 * row["negative_rate"]
        label = (
            f"{row['use_case']} TOP-{x}: {row['negative']}/"
            f"{row['positive'] + row['negative']} negativi"
        )
        ax.scatter([x], [y], s=65, color=colors[index % len(colors)], label=label, zorder=3)
        ax.annotate(
            f"{y:.1f}%",
            xy=(x, y),
            xytext=(5, 7 + 7 * (index % 2)),
            textcoords="offset points",
            fontsize=8,
            color=colors[index % len(colors)],
        )

    ax.set_xlabel("numero di candidati valutati K")
    ax.set_ylabel("campioni con etichetta negativa (%)")
    ax.set_title(
        f"Audit v2 delle etichette: {factorable} outcome su {n_cells} danno fattori",
        fontsize=11,
    )
    ax.set_xlim(0.5, max_k + 0.5)
    ax.set_ylim(0, 100)
    ax.legend(fontsize=7.5, loc="best")
    ax.grid(alpha=0.3)
    return _save(fig, output_dir, "tetto_classe_negativa")


def generate_all(
    *, mode_json: Path, fraction_json: Path, training_json: Path, output_dir: Path
) -> dict:
    mode, fraction, training, signature = load_inputs(
        mode_json, fraction_json, training_json
    )
    outputs = []
    outputs.extend(fig_istogramma_moda_zero(mode, output_dir))
    outputs.extend(fig_frazione_efficace(fraction, training, output_dir))
    outputs.extend(fig_tetto_classe_negativa(mode, training, output_dir))
    provenance = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "classifier-audit-figures-provenance",
        "inputs": {
            "mode_json": str(Path(mode_json).resolve()),
            "fraction_json": str(Path(fraction_json).resolve()),
            "training_json": str(Path(training_json).resolve()),
        },
        "manifest_signature": signature,
        "outputs": [str(path.resolve()) for path in outputs],
    }
    provenance_path = output_dir / "audit_classificatore_figures_v2.json"
    provenance_path.write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {**provenance, "provenance_path": str(provenance_path.resolve())}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode-json", type=Path, required=True)
    parser.add_argument("--fraction-json", type=Path, required=True)
    parser.add_argument("--training-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = generate_all(
            mode_json=args.mode_json,
            fraction_json=args.fraction_json,
            training_json=args.training_json,
            output_dir=args.output_dir,
        )
    except (ArtifactError, OSError) as exc:
        raise SystemExit(f"Errore negli artefatti v2: {exc}") from exc
    print(f"Provenienza: {result['provenance_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
