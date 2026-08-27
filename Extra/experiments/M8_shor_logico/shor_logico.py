"""M8 — proxy fenomenologico di Shor con errore logico per gate.

``p_L`` e' definito qui come probabilita' totale che, dopo ogni porta compilata
inclusa nel modello, venga applicato un Pauli non-identita'. Non e' il parametro
``lambda`` del canale
depolarizzante di Aer: su ``q`` qubit si usa

    lambda_q = p_L * 4**q / (4**q - 1).

Il modello e' un proxy uniforme per gate nella base compilata RZ/SX/X/CX. RZ e'
virtuale; p_L e' applicato a SX/X e CX. Non e' una equivalenza diretta con le
metriche aggregate o per ciclo di M6/M7: eventuali regimi QEC sovrapposti alle
figure devono essere forniti e giustificati esternamente.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from statistics import NormalDist

import numpy as np
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error


_HERE = Path(__file__).resolve().parent
sys.path.insert(0, os.fspath(_HERE.parent / "campagne_classiche_M1-M4"))
from shor_core import (  # noqa: E402
    compile_shor_circuit,
    experiment_manifest,
    extract_factors,
)


SCHEMA_VERSION = "2.0"
M8_REVISION = "m8-logical-pauli-proxy-v2-replicated"
LOGICAL_NOISE_REVISION = "phenomenological-pauli-per-gate-v2"
DEFAULT_P_GRID = [
    0.0,
    0.0001,
    0.0005,
    0.001,
    0.0017,
    0.002,
    0.005,
    0.01,
    0.02,
    0.05,
    0.10,
    0.20,
    0.50,
]


def validate_p_grid(values) -> list[float]:
    """Require a finite, strictly increasing grid starting with exactly one zero."""
    if not isinstance(values, (list, tuple)) or len(values) < 2:
        raise ValueError("p-grid deve contenere almeno due punti.")
    grid = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Ogni p_L deve essere numerico.")
        point = float(value)
        if not math.isfinite(point) or not 0.0 <= point <= 1.0:
            raise ValueError("Ogni p_L deve essere finito e appartenere a [0, 1].")
        grid.append(point)
    if grid[0] != 0.0 or grid.count(0.0) != 1:
        raise ValueError("p-grid deve iniziare con un unico punto p_L=0.")
    if any(right <= left for left, right in zip(grid, grid[1:])):
        raise ValueError("p-grid deve essere strettamente crescente e senza duplicati.")
    return grid


def validate_run_parameters(shots: int, replicates: int, seed: int, confidence: float) -> None:
    if type(shots) is not int or shots < 1:
        raise ValueError("shots deve essere un intero positivo.")
    if type(replicates) is not int or replicates < 2:
        raise ValueError("replicates deve essere un intero >= 2.")
    if type(seed) is not int or not 0 <= seed <= 2 ** 32 - 1:
        raise ValueError("seed deve essere un intero unsigned a 32 bit.")
    if not isinstance(confidence, (int, float)) or not 0.0 < float(confidence) < 1.0:
        raise ValueError("confidence deve appartenere a (0, 1).")


def depolarizing_lambda(p_L: float, num_qubits: int) -> float:
    """Convert total non-identity Pauli probability to Aer lambda."""
    if isinstance(p_L, bool) or not isinstance(p_L, (int, float)):
        raise ValueError("p_L deve essere numerico.")
    p_L = float(p_L)
    if not math.isfinite(p_L) or not 0.0 <= p_L <= 1.0:
        raise ValueError("p_L deve essere in [0, 1].")
    if type(num_qubits) is not int or num_qubits < 1:
        raise ValueError("num_qubits deve essere un intero positivo.")
    dimension_squared = 4 ** num_qubits
    return p_L * dimension_squared / (dimension_squared - 1)


def logical_pauli_error(p_L: float, num_qubits: int):
    """Aer QuantumError whose total non-identity Pauli probability is p_L."""
    return depolarizing_error(depolarizing_lambda(p_L, num_qubits), num_qubits)


def logical_noise(p_L: float) -> NoiseModel:
    """Uniform phenomenological logical-Pauli proxy on physical compiled gates."""
    model = NoiseModel()
    if float(p_L) == 0.0:
        # Validate zero as well, but keep an actually empty ideal model.
        depolarizing_lambda(p_L, 1)
        return model
    model.add_all_qubit_quantum_error(logical_pauli_error(p_L, 1), ["sx", "x"])
    model.add_all_qubit_quantum_error(logical_pauli_error(p_L, 2), ["cx"])
    return model


def logical_noise_manifest() -> dict:
    return {
        "revision": LOGICAL_NOISE_REVISION,
        "kind": "phenomenological_per_gate_proxy",
        "p_L_definition": (
            "total_probability_of_nonidentity_Pauli_after_each_modeled_compiled_gate"
        ),
        "aer_lambda": {"1q": "4*p_L/3", "2q": "16*p_L/15"},
        "gate_scope": {"1q": ["sx", "x"], "2q": ["cx"], "virtual": ["rz"]},
        "direct_equivalence_to_M6_M7": False,
        "interpretation": (
            "Proxy uniforme per gate; non convertire direttamente metriche per ciclo, "
            "round o memoria di M6/M7 in p_L senza un modello di mapping separato."
        ),
    }


def wilson_interval(successes: int, total: int, confidence: float = 0.95) -> dict:
    if type(successes) is not int or type(total) is not int or total <= 0:
        raise ValueError("successes e total devono essere interi con total > 0.")
    if not 0 <= successes <= total:
        raise ValueError("successes deve appartenere a [0, total].")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence deve appartenere a (0, 1).")
    z = NormalDist().inv_cdf(0.5 + confidence / 2.0)
    estimate = successes / total
    denominator = 1.0 + z * z / total
    centre = (estimate + z * z / (2.0 * total)) / denominator
    margin = z * math.sqrt(
        estimate * (1.0 - estimate) / total + z * z / (4.0 * total * total)
    ) / denominator
    return {
        "low": max(0.0, centre - margin),
        "high": min(1.0, centre + margin),
        "confidence": float(confidence),
        "method": "Wilson score",
    }


def derived_seed(base_seed: int, point_index: int, replicate_index: int, stream: int = 0) -> int:
    """Stable independent uint32 streams for simulator and tie-breaking consumers."""
    return int(
        (
            base_seed
            + 1_000_003 * (point_index + 1)
            + 97_409 * (replicate_index + 1)
            + 65_537 * stream
        )
        % (2 ** 32)
    )


def _count_factor_successes(counts: dict, N: int, a: int, n_count: int) -> int:
    return sum(
        count
        for bits, count in counts.items()
        if extract_factors(int(str(bits).replace(" ", ""), 2), n_count, N, a)[0]
        is not None
    )


def evaluate_point(
    tqc,
    N: int,
    a: int,
    n_count: int,
    p_L: float,
    shots: int,
    replicates: int,
    seed: int,
    point_index: int,
    confidence: float = 0.95,
) -> dict:
    simulator = (
        AerSimulator(method="matrix_product_state")
        if p_L == 0.0
        else AerSimulator(noise_model=logical_noise(p_L), method="matrix_product_state")
    )
    replica_results = []
    total_successes = 0
    for replicate in range(replicates):
        simulator_seed = derived_seed(seed, point_index, replicate)
        counts = simulator.run(
            tqc, shots=shots, seed_simulator=simulator_seed
        ).result().get_counts()
        actual_shots = int(sum(counts.values()))
        successes = int(_count_factor_successes(counts, N, a, n_count))
        total_successes += successes
        replica_results.append(
            {
                "replicate": replicate,
                "simulator_seed": simulator_seed,
                "successes": successes,
                "shots": actual_shots,
                "P_success": successes / actual_shots,
            }
        )

    total_shots = sum(item["shots"] for item in replica_results)
    estimate = total_successes / total_shots
    binomial_se = math.sqrt(estimate * (1.0 - estimate) / total_shots)
    replicate_values = np.asarray(
        [item["P_success"] for item in replica_results], dtype=float
    )
    replicate_sd = float(np.std(replicate_values, ddof=1))
    replicate_se = replicate_sd / math.sqrt(replicates)
    # Conservative guard against between-run overdispersion.
    uncertainty_se = max(binomial_se, replicate_se)
    return {
        "p_L": p_L,
        "P_success": estimate,
        "successes": total_successes,
        "total_shots": total_shots,
        "P_success_se": binomial_se,
        "replicate_mean": float(np.mean(replicate_values)),
        "replicate_sd": replicate_sd,
        "replicate_se": replicate_se,
        "uncertainty_se": uncertainty_se,
        "wilson_ci": wilson_interval(total_successes, total_shots, confidence),
        "replicates": replica_results,
    }


def assess_monotonicity(points: list[dict], confidence: float = 0.95) -> dict:
    """Test adjacent non-increase with combined uncertainty and family-wise coverage."""
    if len(points) < 2:
        raise ValueError("Servono almeno due punti per valutare la monotonia.")
    comparisons_count = len(points) - 1
    component_confidence = 1.0 - (1.0 - confidence) / comparisons_count
    z = NormalDist().inv_cdf(0.5 + component_confidence / 2.0)
    comparisons = []
    for left, right in zip(points, points[1:]):
        drop = float(left["P_success"] - right["P_success"])
        combined_se = math.hypot(
            float(left["uncertainty_se"]), float(right["uncertainty_se"])
        )
        low = drop - z * combined_se
        high = drop + z * combined_se
        comparisons.append(
            {
                "p_L_left": left["p_L"],
                "p_L_right": right["p_L"],
                "estimated_drop": drop,
                "combined_se": combined_se,
                "drop_ci": {
                    "low": low,
                    "high": high,
                    "confidence": component_confidence,
                    "method": (
                        "normal difference with combined point uncertainty and "
                        "Bonferroni adjustment"
                    ),
                },
                "compatible_with_nonincrease": high >= 0.0,
                "confirmed_decrease": low > 0.0,
            }
        )
    return {
        "criterion": (
            "monotone-compatible iff no adjacent increase is significant after combining "
            "the uncertainty of both point estimates with Bonferroni family-wise control"
        ),
        "familywise_confidence": float(confidence),
        "component_confidence": component_confidence,
        "monotone_compatible": all(
            item["compatible_with_nonincrease"] for item in comparisons
        ),
        "all_adjacent_decreases_confirmed": all(
            item["confirmed_decrease"] for item in comparisons
        ),
        "comparisons": comparisons,
    }


def run_curve(
    N: int,
    a: int,
    n_count: int,
    p_list,
    shots: int,
    replicates: int,
    seed: int,
    confidence: float = 0.95,
) -> dict:
    grid = validate_p_grid(p_list)
    validate_run_parameters(shots, replicates, seed, confidence)
    tqc = compile_shor_circuit(N, a, n_count)
    print(
        f"\n=== SHOR LOGICO — N={N}, a={a}, {replicates} repliche x "
        f"{shots} shot/punto ==="
    )
    points = []
    for point_index, p_L in enumerate(grid):
        point = evaluate_point(
            tqc,
            N,
            a,
            n_count,
            p_L,
            shots,
            replicates,
            seed,
            point_index,
            confidence,
        )
        points.append(point)
        interval = point["wilson_ci"]
        print(
            f"p_L={p_L:<9g} P_success={point['P_success']:.4f} "
            f"CI {confidence:.1%}=[{interval['low']:.4f}, {interval['high']:.4f}]",
            flush=True,
        )
    monotonicity = assess_monotonicity(points, confidence)
    print(
        "Monotonia compatibile con l'incertezza combinata: "
        f"{'si' if monotonicity['monotone_compatible'] else 'NO'}"
    )
    return {
        "N": N,
        "a": a,
        "n_count": n_count,
        "shots_per_replicate": shots,
        "replicate_count": replicates,
        "confidence": float(confidence),
        "p_grid": grid,
        "points": points,
        "P_ideal": points[0]["P_success"],
        "P_at_max_p": points[-1]["P_success"],
        "monotonicity": monotonicity,
    }


def build_payload(args, curve: dict) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "milestone": "M8_shor_logico",
        "revision": M8_REVISION,
        "generated_at": datetime.now().astimezone().isoformat(),
        "config": {
            "N": args.N,
            "a": args.a,
            "n_count": args.n_count,
            "shots_per_replicate": args.shots,
            "replicate_count": args.replicates,
            "seed": args.seed,
            "confidence": args.confidence,
            "p_grid": curve["p_grid"],
        },
        "logical_noise_manifest": logical_noise_manifest(),
        "circuit_manifest": experiment_manifest(args.N, args.a, args.n_count),
        "curve": curve,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="M8 — proxy logico per-gate replicato")
    parser.add_argument("--N", type=int, default=15)
    parser.add_argument("--a", type=int, default=7)
    parser.add_argument("--n-count", "--n_count", dest="n_count", type=int, default=8)
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--replicates", "--reps", dest="replicates", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--p-list", type=float, nargs="+", default=DEFAULT_P_GRID)
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    return parser


def main(argv=None) -> Path:
    args = build_parser().parse_args(argv)
    try:
        curve = run_curve(
            args.N,
            args.a,
            args.n_count,
            args.p_list,
            args.shots,
            args.replicates,
            args.seed,
            args.confidence,
        )
    except ValueError as error:
        raise SystemExit(f"Configurazione non valida: {error}") from error
    payload = build_payload(args, curve)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    filename = args.output_dir / (
        f"results_M8_shor_logico_v2_{datetime.now():%Y%m%d_%H%M%S}.json"
    )
    with filename.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)
    print(f"Risultati salvati in: {filename}")
    return filename


if __name__ == "__main__":
    main()
