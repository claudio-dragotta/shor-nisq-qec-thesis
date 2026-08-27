"""Diagnostico v2: frequenza della moda sterile ``y=0`` nel preset UC1.

Il modulo non esegue nulla all'import. La CLI compila il circuito tramite il contratto
congelato di :mod:`shor_core`, applica il tie-break riproducibile delle campagne v2 e salva
un JSON autosufficiente per l'audit e per ``figure_src/gen_audit_classificatore.py``.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from qiskit_aer import AerSimulator

from shor_core import (
    build_noise_model,
    compile_shor_circuit,
    experiment_manifest,
    extract_factors,
    rank_measurements,
)

SCHEMA_VERSION = "2.0"
ARTIFACT_TYPE = "phase1-mode-zero-uc1"
OUTPUT_NAME = "diagnostic_mode_zero_uc1_v2.json"
N, A, N_COUNT = 15, 7, 8
THEORETICAL_PEAKS = (0, 64, 128, 192)
UC1_NOISE = {
    "eps_1q": 1e-3,
    "eps_2q": 1e-2,
    "t1_ns": 100_000,
    "t2_ns": 80_000,
    "p_ro": 0.02,
}
MAX_AER_SEED = 2**31 - 1


def factor_success(value: int) -> bool:
    """Restituisce se il post-processing v2 ricava fattori non banali da ``value``."""
    p, q = extract_factors(int(value), N_COUNT, N, A)
    return p is not None and q is not None and p * q == N


def simulation_seeds(seed: int, reps: int) -> list[int]:
    """Semi disgiunti secondo lo schedule congelato delle campagne v2."""
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed deve essere un intero non negativo.")
    if isinstance(reps, bool) or not isinstance(reps, int) or reps < 1:
        raise ValueError("reps deve essere un intero positivo.")
    seeds = [seed * 1_000_000 + iteration * 10_000 for iteration in range(1, reps + 1)]
    if seeds[-1] > MAX_AER_SEED:
        raise ValueError(
            "La combinazione seed/reps supera il massimo seed Aer 2147483647."
        )
    return seeds


def analyse_counts(counts: Mapping[str, int], tie_seed: int) -> dict:
    """Analizza un istogramma senza dipendere dall'ordine del dizionario Aer."""
    if not counts:
        raise ValueError("L'istogramma non può essere vuoto.")
    total = int(sum(int(count) for count in counts.values()))
    if total <= 0:
        raise ValueError("Il numero totale di shot deve essere positivo.")

    ranked = rank_measurements(counts, tie_seed)
    ordered = []
    for rank, (bits, count) in enumerate(ranked[:4], start=1):
        value = int(str(bits).replace(" ", ""), 2)
        ordered.append(
            {
                "rank": rank,
                "value": value,
                "count": int(count),
                "probability": float(count) / total,
                "factor_success": factor_success(value),
            }
        )

    histogram = [0] * (2**N_COUNT)
    for bits, count in counts.items():
        value = int(str(bits).replace(" ", ""), 2)
        if not 0 <= value < len(histogram):
            raise ValueError(f"Outcome fuori dal registro a {N_COUNT} bit: {bits!r}.")
        histogram[value] += int(count)

    peak_mass = sum(histogram[value] for value in THEORETICAL_PEAKS) / total
    top_value = ordered[0]["value"]
    return {
        "seed_simulator": int(tie_seed),
        "shots": total,
        "top_value": top_value,
        "mode_is_zero": top_value == 0,
        "mode_factor_success": bool(ordered[0]["factor_success"]),
        "top4_factor_success": any(row["factor_success"] for row in ordered),
        "peak_mass": float(peak_mass),
        "ordered_top4": ordered,
        "histogram_counts": histogram,
    }


def _reference_data() -> dict:
    factorable = [value for value in range(2**N_COUNT) if factor_success(value)]
    return {
        "theoretical_peaks": list(THEORETICAL_PEAKS),
        "useful_theoretical_peaks": [
            value for value in THEORETICAL_PEAKS if factor_success(value)
        ],
        "factorable_outcomes": factorable,
        "factorable_outcome_count": len(factorable),
        "uniform_top1_factor_floor": len(factorable) / (2**N_COUNT),
    }


def run_diagnostic(*, seed: int, shots: int, reps: int) -> dict:
    """Esegue il diagnostico con circuito e ranking del contratto v2."""
    if isinstance(shots, bool) or not isinstance(shots, int) or not 1 <= shots <= 10_000:
        raise ValueError("shots deve essere un intero tra 1 e 10000 per lo schedule dei seed.")
    seeds = simulation_seeds(seed, reps)
    compiled = compile_shor_circuit(N, A, N_COUNT)
    simulator = AerSimulator(
        noise_model=build_noise_model(**UC1_NOISE), method="statevector"
    )

    records = []
    mode_zero_candidates = []
    modes: Counter[int] = Counter()
    for rep, simulation_seed in enumerate(seeds, start=1):
        counts = simulator.run(
            compiled, shots=shots, seed_simulator=simulation_seed
        ).result().get_counts()
        record = analyse_counts(counts, simulation_seed)
        histogram = record.pop("histogram_counts")
        record["rep"] = rep
        records.append(record)
        modes[record["top_value"]] += 1
        if record["mode_is_zero"]:
            mode_zero_candidates.append({**record, "histogram_counts": histogram})

    representative = None
    if mode_zero_candidates:
        candidates = sorted(
            mode_zero_candidates, key=lambda row: (row["peak_mass"], row["rep"])
        )
        representative = candidates[len(candidates) // 2]

    mode_zero_count = sum(row["mode_is_zero"] for row in records)
    mode_success_count = sum(row["mode_factor_success"] for row in records)
    top4_success_count = sum(row["top4_factor_success"] for row in records)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "N": N,
            "a": A,
            "n_count": N_COUNT,
            "use_case": "UC1",
            "noise": dict(UC1_NOISE),
            "shots": shots,
            "reps": reps,
            "seed": seed,
            "seed_schedule": "seed*1000000 + rep*10000; rep starts at 1",
        },
        "manifest": experiment_manifest(N, A, N_COUNT),
        "methodology": {
            "ranking": "rank_measurements con tie-break SHA-256 dipendente dal seed",
            "representative_mode_zero": (
                "mediana superiore della massa sui quattro picchi fra le repliche con moda y=0; "
                "pareggio risolto per indice di replica"
            ),
        },
        "reference": _reference_data(),
        "summary": {
            "mode_zero_count": mode_zero_count,
            "mode_zero_rate": mode_zero_count / reps,
            "mode_factor_success_count": mode_success_count,
            "mode_factor_success_rate": mode_success_count / reps,
            "top4_factor_success_count": top4_success_count,
            "top4_factor_success_rate": top4_success_count / reps,
            "mode_distribution": [
                {"value": value, "count": count, "rate": count / reps}
                for value, count in sorted(
                    modes.items(), key=lambda item: (-item[1], item[0])
                )
            ],
        },
        "runs": records,
        "representative_mode_zero": representative,
    }


def write_artifact(payload: dict, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / OUTPUT_NAME
    with path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    return path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--shots", type=int, default=1024)
    parser.add_argument("--reps", type=int, default=60)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = run_diagnostic(seed=args.seed, shots=args.shots, reps=args.reps)
    output = write_artifact(payload, args.output_dir)
    summary = payload["summary"]
    print(f"Artefatto v2: {output}")
    print(
        f"moda y=0: {summary['mode_zero_count']}/{args.reps} "
        f"({summary['mode_zero_rate']:.1%})"
    )
    print(
        f"moda utile: {summary['mode_factor_success_count']}/{args.reps} "
        f"({summary['mode_factor_success_rate']:.1%})"
    )
    print(
        f"TOP-4 utile: {summary['top4_factor_success_count']}/{args.reps} "
        f"({summary['top4_factor_success_rate']:.1%})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
