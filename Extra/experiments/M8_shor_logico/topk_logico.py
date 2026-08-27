"""M13 — TOP-K sul proxy logico M8, con pareggi e repliche espliciti.

Ogni replica produce un solo istogramma, riusato per la metrica per-misura,
TOP-K e TOP-1. Se il K-esimo posto cade in un gruppo di esiti a pari conteggio,
il risultato non e' identificato univocamente: salviamo quindi il limite
inferiore, una selezione pseudo-casuale riproducibile e il limite superiore.

Come in :mod:`shor_logico`, ``p_L`` e' un proxy fenomenologico per gate e non
una conversione diretta delle metriche M6/M7.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

from qiskit_aer import AerSimulator


_HERE = Path(__file__).resolve().parent
sys.path.insert(0, os.fspath(_HERE.parent / "campagne_classiche_M1-M4"))
from shor_core import (  # noqa: E402
    compile_shor_circuit,
    experiment_manifest,
    extract_factors,
)
from shor_logico import (  # noqa: E402
    SCHEMA_VERSION,
    assess_monotonicity,
    derived_seed,
    logical_noise,
    logical_noise_manifest,
    validate_p_grid,
    validate_run_parameters,
    wilson_interval,
)


N = 15
A = 7
N_COUNT = 8
M13_REVISION = "m13-topk-logical-tie-aware-v2"
DEFAULT_P_GRID = [
    0.0, 0.0001, 0.0005, 0.001, 0.0017, 0.002,
    0.005, 0.01, 0.02, 0.05, 0.10, 0.20,
]


def _clean_bits(bits: str) -> str:
    cleaned = str(bits).replace(" ", "")
    if not cleaned or any(bit not in "01" for bit in cleaned):
        raise ValueError(f"Esito di misura non binario: {bits!r}.")
    return cleaned


def is_factor_success(bits: str, N: int = N, a: int = A, n_count: int = N_COUNT) -> bool:
    measured = int(_clean_bits(bits), 2)
    return extract_factors(measured, n_count, N, a)[0] is not None


def resolve_top_k(
    counts: dict[str, int],
    K: int,
    tie_seed: int,
    success_predicate: Callable[[str], bool] | None = None,
) -> dict:
    """Resolve TOP-K and identify its bounds when the boundary is tied.

    ``lower_success`` is true only if *every* admissible choice from the tied
    boundary contains a successful outcome; ``upper_success`` is true if at
    least one admissible choice can contain one. ``seeded_success`` uses a
    uniform sample without replacement from the sorted boundary group.
    """
    if type(K) is not int or K < 1:
        raise ValueError("K deve essere un intero positivo.")
    if type(tie_seed) is not int or not 0 <= tie_seed <= 2 ** 32 - 1:
        raise ValueError("tie_seed deve essere un intero unsigned a 32 bit.")
    if not isinstance(counts, dict) or not counts:
        raise ValueError("counts non puo' essere vuoto.")

    normalized: dict[str, int] = {}
    for raw_bits, raw_count in counts.items():
        bits = _clean_bits(raw_bits)
        if type(raw_count) is not int or raw_count <= 0:
            raise ValueError("I conteggi devono essere interi positivi.")
        normalized[bits] = normalized.get(bits, 0) + raw_count

    predicate = success_predicate or is_factor_success
    ranked = sorted(normalized.items(), key=lambda item: (-item[1], int(item[0], 2)))
    effective_k = min(K, len(ranked))
    boundary_count = ranked[effective_k - 1][1]
    mandatory = [bits for bits, count in ranked if count > boundary_count]
    boundary = [bits for bits, count in ranked if count == boundary_count]
    slots = effective_k - len(mandatory)
    if not 0 < slots <= len(boundary):
        raise RuntimeError("Partizione TOP-K al confine incoerente.")

    rng = random.Random(tie_seed)
    selected_boundary = sorted(
        rng.sample(sorted(boundary, key=lambda bits: int(bits, 2)), slots),
        key=lambda bits: int(bits, 2),
    )
    selected = mandatory + selected_boundary

    mandatory_success = any(predicate(bits) for bits in mandatory)
    good_boundary = sum(bool(predicate(bits)) for bits in boundary)
    bad_boundary = len(boundary) - good_boundary
    lower_success = mandatory_success or slots > bad_boundary
    upper_success = mandatory_success or (slots > 0 and good_boundary > 0)
    seeded_success = any(predicate(bits) for bits in selected)
    if not (lower_success <= seeded_success <= upper_success):
        raise RuntimeError("La selezione seeded viola i limiti identificati del pareggio.")

    return {
        "requested_k": K,
        "effective_k": effective_k,
        "seeded_success": bool(seeded_success),
        "lower_success": bool(lower_success),
        "upper_success": bool(upper_success),
        "selected_outcomes": selected,
        "mandatory_outcomes": mandatory,
        "selected_boundary_outcomes": selected_boundary,
        "boundary": {
            "count": boundary_count,
            "outcomes": boundary,
            "size": len(boundary),
            "slots": slots,
            "successful_outcomes": good_boundary,
            "tie_present": len(boundary) > slots,
        },
    }


def _binary_summary(values: list[bool], confidence: float) -> dict:
    if not values:
        raise ValueError("Servono almeno due esiti replicati.")
    successes = int(sum(bool(value) for value in values))
    total = len(values)
    estimate = successes / total
    return {
        "estimate": estimate,
        "successes": successes,
        "total": total,
        "standard_error": math.sqrt(estimate * (1.0 - estimate) / total),
        "wilson_ci": wilson_interval(successes, total, confidence),
    }


def _measure_summary(successes: int, total: int, confidence: float) -> dict:
    estimate = successes / total
    return {
        "estimate": estimate,
        "successes": successes,
        "total": total,
        "standard_error": math.sqrt(estimate * (1.0 - estimate) / total),
        "wilson_ci": wilson_interval(successes, total, confidence),
    }


def _run_replica(tqc, simulator, shots: int, simulator_seed: int, tie_seed: int, K: int) -> dict:
    raw_counts = simulator.run(
        tqc, shots=shots, seed_simulator=simulator_seed
    ).result().get_counts()
    counts = {
        _clean_bits(bits): int(count)
        for bits, count in sorted(
            raw_counts.items(), key=lambda item: int(_clean_bits(item[0]), 2)
        )
    }
    actual_shots = int(sum(counts.values()))
    factor_successes = int(
        sum(count for bits, count in counts.items() if is_factor_success(bits))
    )
    return {
        "simulator_seed": simulator_seed,
        "tie_seed": tie_seed,
        "shots": actual_shots,
        "factor_successes": factor_successes,
        "per_measure": factor_successes / actual_shots,
        "topk": resolve_top_k(counts, K, tie_seed),
        "top1": resolve_top_k(counts, 1, tie_seed),
        "counts": counts,
    }


def evaluate_point(
    tqc,
    p_L: float,
    shots: int,
    replicates: int,
    K: int,
    seed: int,
    point_index: int,
    confidence: float,
) -> dict:
    simulator = (
        AerSimulator(method="matrix_product_state")
        if p_L == 0.0
        else AerSimulator(noise_model=logical_noise(p_L), method="matrix_product_state")
    )
    replica_results = []
    for replicate in range(replicates):
        simulator_seed = derived_seed(seed, point_index, replicate, stream=0)
        tie_seed = derived_seed(seed, point_index, replicate, stream=1)
        result = _run_replica(tqc, simulator, shots, simulator_seed, tie_seed, K)
        result["replicate"] = replicate
        replica_results.append(result)

    total_shots = sum(item["shots"] for item in replica_results)
    total_factor_successes = sum(item["factor_successes"] for item in replica_results)

    def top_summary(key: str) -> dict:
        return {
            "seeded_estimate": _binary_summary(
                [item[key]["seeded_success"] for item in replica_results], confidence
            ),
            "lower_bound": _binary_summary(
                [item[key]["lower_success"] for item in replica_results], confidence
            ),
            "upper_bound": _binary_summary(
                [item[key]["upper_success"] for item in replica_results], confidence
            ),
        }

    return {
        "p_L": p_L,
        "shots_per_replicate": shots,
        "replicate_count": replicates,
        "per_measure": _measure_summary(
            total_factor_successes, total_shots, confidence
        ),
        "topk": top_summary("topk"),
        "top1": top_summary("top1"),
        "replicates": replica_results,
    }


def difference_interval(
    first: dict, last: dict, confidence: float = 0.95
) -> dict:
    """Newcombe hybrid-score interval for two independent proportions (p0-p1)."""
    first_p = float(first["estimate"])
    last_p = float(last["estimate"])
    first_ci = first["wilson_ci"]
    last_ci = last["wilson_ci"]
    estimate = first_p - last_p
    low = estimate - math.hypot(
        first_p - float(first_ci["low"]),
        float(last_ci["high"]) - last_p,
    )
    high = estimate + math.hypot(
        float(first_ci["high"]) - first_p,
        last_p - float(last_ci["low"]),
    )
    return {
        "estimate": estimate,
        "low": max(-1.0, low),
        "high": min(1.0, high),
        "confidence": float(confidence),
        "method": "Newcombe hybrid score (independent Wilson intervals)",
    }


def equivalence_test(
    first: dict,
    last: dict,
    margin: float,
    confidence: float = 0.95,
) -> dict:
    if not 0.0 < margin < 1.0:
        raise ValueError("equivalence_margin deve appartenere a (0, 1).")
    interval = difference_interval(first, last, confidence)
    equivalent = interval["low"] > -margin and interval["high"] < margin
    discriminating_decrease = interval["low"] > margin
    return {
        "contrast": "p_L=0 minus p_L=max",
        "equivalence_margin": margin,
        "interval": interval,
        "equivalent": equivalent,
        "discriminating_decrease": discriminating_decrease,
        "decision_rule": (
            "equivalent iff the complete confidence interval is inside "
            "[-margin, +margin]; discriminating decrease iff its lower bound exceeds margin"
        ),
    }


def tie_robust_equivalence(
    first_topk: dict,
    last_topk: dict,
    margin: float,
    confidence: float,
) -> dict:
    """Envelope uncertainty and every admissible resolution of boundary ties.

    Four endpoint proportions enter the envelope.  Their Wilson intervals use
    a Bonferroni component confidence of ``1 - (1-confidence)/4``, so the
    reported envelope has at least the requested simultaneous coverage under
    the independent-replica model.
    """
    first_lower = first_topk["lower_bound"]
    first_upper = first_topk["upper_bound"]
    last_lower = last_topk["lower_bound"]
    last_upper = last_topk["upper_bound"]
    component_confidence = 1.0 - (1.0 - confidence) / 4.0

    def adjusted_interval(summary: dict) -> dict:
        return wilson_interval(
            int(summary["successes"]), int(summary["total"]), component_confidence
        )

    first_lower_ci = adjusted_interval(first_lower)
    first_upper_ci = adjusted_interval(first_upper)
    last_lower_ci = adjusted_interval(last_lower)
    last_upper_ci = adjusted_interval(last_upper)
    low = (
        float(first_lower_ci["low"])
        - float(last_upper_ci["high"])
    )
    high = (
        float(first_upper_ci["high"])
        - float(last_lower_ci["low"])
    )
    return {
        "contrast": "p_L=0 minus p_L=max",
        "identified_confidence_envelope": {
            "low": max(-1.0, low),
            "high": min(1.0, high),
            "confidence": float(confidence),
            "component_confidence": component_confidence,
            "method": (
                "Bonferroni-adjusted Wilson envelope over all admissible "
                "boundary-tie resolutions"
            ),
        },
        "equivalence_margin": margin,
        "equivalent_for_all_tie_resolutions": low > -margin and high < margin,
    }


def analysis_plan(K: int, confidence: float, equivalence_margin: float) -> dict:
    """Static, data-independent decision contract saved before interpreting results."""
    return {
        "status": "preregistered_in_script_before_simulation",
        "primary_endpoint": f"seeded TOP-{K} success probability per replicate",
        "primary_contrast": "p_L=0 minus largest preregistered p_L",
        "confidence": float(confidence),
        "interval_method": "Newcombe hybrid score from Wilson intervals",
        "equivalence_margin_absolute": equivalence_margin,
        "equivalence_hypothesis": f"difference strictly inside +/-{equivalence_margin:g}",
        "discrimination_hypothesis": (
            f"lower confidence bound of the decrease exceeds {equivalence_margin:g}"
        ),
        "tie_handling": (
            "uniform seeded sample without replacement at the K-boundary; report lower "
            "and upper identified bounds and a Bonferroni-Wilson tie-robust envelope"
        ),
        "multiplicity": "single primary contrast; remaining p-grid comparisons descriptive",
    }


def checkpoint_identity(
    grid: list[float],
    replicates: int,
    shots: int,
    K: int,
    seed: int,
    confidence: float,
) -> dict:
    """Exact contract used to decide whether a partial run is reusable."""
    manifest = experiment_manifest(N, A, N_COUNT)
    return {
        "revision": M13_REVISION,
        "logical_noise_revision": logical_noise_manifest()["revision"],
        "circuit_sha256": manifest["circuit_sha256"],
        "N": N,
        "a": A,
        "n_count": N_COUNT,
        "K": K,
        "shots_per_replicate": shots,
        "replicate_count": replicates,
        "seed": seed,
        "confidence": float(confidence),
        "p_grid": grid,
    }


def _write_checkpoint(path: Path, identity: dict, points: list[dict], status: str) -> None:
    """Atomically persist full replica data after every completed grid point."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "milestone": "M13_topk_logico_checkpoint",
        "revision": M13_REVISION,
        "status": status,
        "identity": identity,
        "completed_points": points,
    }
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _load_checkpoint(path: Path, identity: dict) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    if (
        payload.get("schema_version") != SCHEMA_VERSION
        or payload.get("milestone") != "M13_topk_logico_checkpoint"
        or payload.get("revision") != M13_REVISION
    ):
        raise ValueError(f"Checkpoint incompatibile: {path}")
    if payload.get("identity") != identity:
        raise ValueError(
            "Il checkpoint esistente appartiene a una configurazione diversa; "
            "specificare un altro --checkpoint oppure archiviarlo esplicitamente."
        )
    points = payload.get("completed_points")
    if not isinstance(points, list):
        raise ValueError("Checkpoint privo della lista completed_points.")
    expected_prefix = identity["p_grid"][: len(points)]
    actual_prefix = [point.get("p_L") for point in points]
    if actual_prefix != expected_prefix:
        raise ValueError("Il checkpoint non contiene un prefisso valido della griglia p_L.")
    return points


def run_curve(
    p_list,
    replicates: int,
    shots: int,
    K: int,
    seed: int,
    confidence: float,
    checkpoint_path: Path | None = None,
) -> dict:
    grid = validate_p_grid(p_list)
    validate_run_parameters(shots, replicates, seed, confidence)
    if type(K) is not int or not 1 <= K <= 2 ** N_COUNT:
        raise ValueError(f"K deve essere un intero in [1, {2 ** N_COUNT}].")

    tqc = compile_shor_circuit(N, A, N_COUNT)
    identity = checkpoint_identity(grid, replicates, shots, K, seed, confidence)
    points = (
        _load_checkpoint(checkpoint_path, identity)
        if checkpoint_path is not None else []
    )
    print(
        f"\n=== M13 TOP-{K} — {replicates} repliche x {shots} shot/punto ==="
    )
    if points:
        print(
            f"Checkpoint ripreso: {len(points)}/{len(grid)} punti completi da "
            f"{checkpoint_path}",
            flush=True,
        )
    for point_index, p_L in enumerate(grid[len(points):], start=len(points)):
        point = evaluate_point(
            tqc, p_L, shots, replicates, K, seed, point_index, confidence
        )
        points.append(point)
        if checkpoint_path is not None:
            _write_checkpoint(checkpoint_path, identity, points, "in_progress")
        topk = point["topk"]
        print(
            f"p_L={p_L:<9g} per-misura={point['per_measure']['estimate']:.4f} "
            f"TOP-{K}={topk['seeded_estimate']['estimate']:.4f} "
            f"identificato=[{topk['lower_bound']['estimate']:.4f}, "
            f"{topk['upper_bound']['estimate']:.4f}]",
            flush=True,
        )

    if checkpoint_path is not None:
        _write_checkpoint(checkpoint_path, identity, points, "curve_complete")

    monotonicity_points = [
        {
            "p_L": point["p_L"],
            "P_success": point["topk"]["seeded_estimate"]["estimate"],
            "uncertainty_se": point["topk"]["seeded_estimate"]["standard_error"],
        }
        for point in points
    ]
    return {
        "p_grid": grid,
        "points": points,
        "monotonicity": assess_monotonicity(monotonicity_points, confidence),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="M13 — TOP-K logico tie-aware replicato")
    parser.add_argument("--replicates", "--iters", dest="replicates", type=int, default=200)
    parser.add_argument("--shots", type=int, default=1024)
    parser.add_argument("--K", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--equivalence-margin", type=float, default=0.10)
    parser.add_argument("--p-list", type=float, nargs="+", default=DEFAULT_P_GRID)
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help=("Checkpoint atomico schema 2. Se omesso usa "
              "<output-dir>/checkpoint_M13_topk_logico_v2.json."),
    )
    return parser


def main(argv=None) -> Path:
    args = build_parser().parse_args(argv)
    if not 0.0 < args.equivalence_margin < 1.0:
        raise SystemExit("Configurazione non valida: equivalence-margin deve essere in (0, 1).")
    checkpoint_path = (
        args.checkpoint
        if args.checkpoint is not None
        else args.output_dir / "checkpoint_M13_topk_logico_v2.json"
    )
    plan = analysis_plan(args.K, args.confidence, args.equivalence_margin)
    try:
        curve = run_curve(
            args.p_list,
            args.replicates,
            args.shots,
            args.K,
            args.seed,
            args.confidence,
            checkpoint_path=checkpoint_path,
        )
    except ValueError as error:
        raise SystemExit(f"Configurazione non valida: {error}") from error

    first = curve["points"][0]["topk"]
    last = curve["points"][-1]["topk"]
    primary = equivalence_test(
        first["seeded_estimate"],
        last["seeded_estimate"],
        args.equivalence_margin,
        args.confidence,
    )
    lower_policy = equivalence_test(
        first["lower_bound"],
        last["lower_bound"],
        args.equivalence_margin,
        args.confidence,
    )
    upper_policy = equivalence_test(
        first["upper_bound"],
        last["upper_bound"],
        args.equivalence_margin,
        args.confidence,
    )
    robust = tie_robust_equivalence(
        first, last, args.equivalence_margin, args.confidence
    )
    if robust["equivalent_for_all_tie_resolutions"]:
        conclusion = "non_discriminating_equivalent_with_tie_robustness"
    elif primary["discriminating_decrease"]:
        conclusion = "discriminating_decrease_primary_seeded_rule"
    elif primary["equivalent"]:
        conclusion = "primary_equivalent_but_tie_sensitive"
    else:
        conclusion = "inconclusive_at_preregistered_margin"

    payload = {
        "schema_version": SCHEMA_VERSION,
        "milestone": "M13_topk_logico",
        "revision": M13_REVISION,
        "generated_at": datetime.now().astimezone().isoformat(),
        "config": {
            "N": N,
            "a": A,
            "n_count": N_COUNT,
            "K": args.K,
            "shots_per_replicate": args.shots,
            "replicate_count": args.replicates,
            "seed": args.seed,
            "confidence": args.confidence,
            "equivalence_margin": args.equivalence_margin,
            "p_grid": curve["p_grid"],
        },
        "logical_noise_manifest": logical_noise_manifest(),
        "circuit_manifest": experiment_manifest(N, A, N_COUNT),
        "analysis_plan": plan,
        "curve": curve,
        "primary_equivalence_test": primary,
        "sensitivity_tests": {
            "always_lower_tie_policy": lower_policy,
            "always_upper_tie_policy": upper_policy,
            "tie_robust": robust,
        },
        "conclusion": conclusion,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    filename = args.output_dir / (
        f"results_M13_topk_logico_v2_{datetime.now():%Y%m%d_%H%M%S}.json"
    )
    with filename.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)
    print(f"\nEsito preregistrato: {conclusion}")
    print(f"Risultati salvati in: {filename}")
    return filename


if __name__ == "__main__":
    main()
