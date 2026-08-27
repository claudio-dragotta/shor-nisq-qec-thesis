"""Diagnostico v2 della frazione efficace del segnale sui picchi QPE.

La frazione è un estimatore descrittivo del modello di miscela ideale-uniforme, non una
misura fisica di coerenza. Il confronto analitico è il proxy di nessun evento Pauli 2Q
``(1 - 15*lambda_2q/16)**n_cx``; non è una probabilità di successo, una fedeltà o una
previsione del rendimento di Shor.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean, pstdev
from typing import Mapping, Sequence

from qiskit_aer import AerSimulator

from shor_core import (
    build_noise_model,
    compile_shor_circuit,
    experiment_manifest,
    rank_measurements,
)

SCHEMA_VERSION = "2.0"
ARTIFACT_TYPE = "phase1-effective-signal-fraction"
OUTPUT_NAME = "diagnostic_effective_signal_fraction_v2.json"
N, A, N_COUNT = 15, 7, 8
PEAKS = (0, 64, 128, 192)
DEFAULT_LAMBDAS_2Q = (1e-3, 5e-3, 1e-2, 2e-2, 5e-2, 1e-1, 2e-1, 3e-1)
BASE_NOISE = {
    "eps_1q": 1e-3,
    "t1_ns": 100_000,
    "t2_ns": 80_000,
    "p_ro": 0.02,
}
MAX_AER_SEED = 2**31 - 1


def simulation_seeds(seed: int, reps: int) -> list[int]:
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


def effective_signal_fraction(peak_mass: float, *, n_peaks: int, n_cells: int) -> float:
    """Stima ``f`` nel modello ``f*P_ideal + (1-f)*P_uniform``."""
    if n_cells <= 0 or not 0 < n_peaks < n_cells:
        raise ValueError("Richiesti 0 < n_peaks < n_cells.")
    uniform_peak_mass = n_peaks / n_cells
    estimate = (float(peak_mass) - uniform_peak_mass) / (1 - uniform_peak_mass)
    return min(1.0, max(0.0, estimate))


def p_no_nonidentity_2q_proxy(lambda_2q: float, n_cx: int) -> float:
    """Proxy indipendente di nessun Pauli 2Q non-identità nel canale depolarizzante.

    Per il parametro Qiskit ``lambda_2q``, la probabilità della componente Pauli non-identità
    di un canale a due qubit è ``15*lambda_2q/16``. Il risultato non rappresenta il successo
    dell'algoritmo né la fedeltà del circuito.
    """
    if not 0 <= float(lambda_2q) <= 1:
        raise ValueError("lambda_2q deve essere in [0, 1].")
    if isinstance(n_cx, bool) or not isinstance(n_cx, int) or n_cx < 0:
        raise ValueError("n_cx deve essere un intero non negativo.")
    return float((1 - 15 * float(lambda_2q) / 16) ** n_cx)


def analyse_counts(counts: Mapping[str, int], tie_seed: int) -> dict:
    if not counts:
        raise ValueError("L'istogramma non può essere vuoto.")
    total = int(sum(int(value) for value in counts.values()))
    if total <= 0:
        raise ValueError("Il numero totale di shot deve essere positivo.")
    ranked = rank_measurements(counts, tie_seed)
    peak_count = sum(
        int(count)
        for bits, count in counts.items()
        if int(str(bits).replace(" ", ""), 2) in PEAKS
    )
    top_value = int(str(ranked[0][0]).replace(" ", ""), 2)
    return {
        "seed_simulator": int(tie_seed),
        "peak_mass": peak_count / total,
        "top_value": top_value,
    }


def run_diagnostic(
    *, seed: int, shots: int, reps: int, lambdas_2q: Sequence[float]
) -> dict:
    if isinstance(shots, bool) or not isinstance(shots, int) or not 1 <= shots <= 10_000:
        raise ValueError("shots deve essere un intero tra 1 e 10000 per lo schedule dei seed.")
    lambdas = [float(value) for value in lambdas_2q]
    if not lambdas:
        raise ValueError("Fornire almeno un valore di lambda_2q.")
    if any(not 0 <= value <= 1 for value in lambdas):
        raise ValueError("Tutti i valori di lambda_2q devono essere in [0, 1].")
    if len(set(lambdas)) != len(lambdas):
        raise ValueError("I valori di lambda_2q devono essere unici.")
    seeds = simulation_seeds(seed, reps)

    compiled = compile_shor_circuit(N, A, N_COUNT)
    n_cx = int(compiled.count_ops().get("cx", 0))
    results = []
    for lambda_2q in lambdas:
        noise = {**BASE_NOISE, "eps_2q": lambda_2q}
        simulator = AerSimulator(
            noise_model=build_noise_model(**noise), method="statevector"
        )
        replicates = []
        modes: Counter[int] = Counter()
        for rep, simulation_seed in enumerate(seeds, start=1):
            counts = simulator.run(
                compiled, shots=shots, seed_simulator=simulation_seed
            ).result().get_counts()
            record = analyse_counts(counts, simulation_seed)
            record["rep"] = rep
            replicates.append(record)
            modes[record["top_value"]] += 1

        masses = [row["peak_mass"] for row in replicates]
        mean_peak_mass = fmean(masses)
        effective_fraction = effective_signal_fraction(
            mean_peak_mass, n_peaks=len(PEAKS), n_cells=2**N_COUNT
        )
        proxy = p_no_nonidentity_2q_proxy(lambda_2q, n_cx)
        results.append(
            {
                "lambda_2q": lambda_2q,
                "mean_peak_mass": mean_peak_mass,
                "peak_mass_std_population": pstdev(masses),
                "effective_signal_fraction": effective_fraction,
                "p_no_nonidentity_2q_proxy": proxy,
                "effective_fraction_to_proxy_ratio": (
                    effective_fraction / proxy if proxy > 0 else None
                ),
                "mode_distribution": [
                    {"value": value, "count": count, "rate": count / reps}
                    for value, count in sorted(
                        modes.items(), key=lambda item: (-item[1], item[0])
                    )
                ],
                "replicates": replicates,
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "N": N,
            "a": A,
            "n_count": N_COUNT,
            "use_case_reference": "UC1",
            "fixed_noise": dict(BASE_NOISE),
            "lambda_2q_values": lambdas,
            "shots": shots,
            "reps": reps,
            "seed": seed,
            "seed_schedule": "seed*1000000 + rep*10000; rep starts at 1",
        },
        "manifest": experiment_manifest(N, A, N_COUNT),
        "methodology": {
            "effective_fraction_model": "P_obs = f*P_ideal + (1-f)*P_uniform",
            "effective_fraction_interpretation": (
                "estimatore descrittivo della massa sui picchi; non misura fisica di coerenza"
            ),
            "proxy_field": "p_no_nonidentity_2q_proxy",
            "proxy_formula": "(1 - 15*lambda_2q/16)**n_cx",
            "proxy_interpretation": (
                "proxy indipendente di nessun evento Pauli 2Q non-identità"
            ),
            "proxy_is_not": [
                "probabilità di successo di Shor",
                "fedeltà del circuito",
                "sopravvivenza fisica del segnale",
            ],
        },
        "circuit": {"n_cx": n_cx, "theoretical_peaks": list(PEAKS)},
        "results": results,
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
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--shots", type=int, default=1024)
    parser.add_argument("--reps", type=int, default=20)
    parser.add_argument(
        "--lambda-2q",
        type=float,
        nargs="+",
        default=list(DEFAULT_LAMBDAS_2Q),
        help="Valori del parametro depolarizzante Qiskit eps_2q/lambda_2q.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = run_diagnostic(
        seed=args.seed,
        shots=args.shots,
        reps=args.reps,
        lambdas_2q=args.lambda_2q,
    )
    output = write_artifact(payload, args.output_dir)
    print(f"Artefatto v2: {output}")
    print(
        f"{'lambda_2q':>10} {'massa picchi':>14} {'f efficace':>12} "
        f"{'proxy no-evento-2Q':>20}"
    )
    for row in payload["results"]:
        print(
            f"{row['lambda_2q']:10.3g} {row['mean_peak_mass']:14.4f} "
            f"{row['effective_signal_fraction']:12.4f} "
            f"{row['p_no_nonidentity_2q_proxy']:20.3e}"
        )
    print("Il proxy non è probabilità di successo, fedeltà o rendimento di Shor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
