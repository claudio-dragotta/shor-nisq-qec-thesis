"""Smoke and input-contract tests for the explicit M8 figure consumers."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest


os.environ.setdefault("MPLBACKEND", "Agg")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gen_shor_logico  # noqa: E402
import gen_shor_pk  # noqa: E402


def _write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    points = [
        {
            "p_L": 0.0,
            "P_success": 0.75,
            "wilson_ci": {"low": 0.70, "high": 0.79},
        },
        {
            "p_L": 0.01,
            "P_success": 0.60,
            "wilson_ci": {"low": 0.55, "high": 0.65},
        },
        {
            "p_L": 0.10,
            "P_success": 0.30,
            "wilson_ci": {"low": 0.25, "high": 0.35},
        },
    ]
    m8_path = tmp_path / "m8.json"
    m8_path.write_text(
        json.dumps(
            {
                "schema_version": "2.0",
                "milestone": "M8_shor_logico",
                "revision": gen_shor_logico.M8_RESULT_REVISION,
                "logical_noise_manifest": {
                    "revision": gen_shor_logico.M8_NOISE_REVISION,
                    "kind": "phenomenological_per_gate_proxy",
                    "direct_equivalence_to_M6_M7": False,
                },
                "circuit_manifest": {
                    "circuit_revision": "shor-qpe-v2-amod15-correct",
                    "postprocess_revision": "seeded-sha256-tie-break-v1",
                    "circuit_sha256": "a" * 64,
                    "basis_gates": ["rz", "sx", "x", "cx"],
                    "seed_transpiler": 42,
                    "gate_counts": {"cx": 224},
                },
                "config": {
                    "N": 15, "a": 7, "n_count": 8,
                    "seed": 42, "replicate_count": 20,
                    "shots_per_replicate": 4096, "confidence": 0.95,
                    "p_grid": [0.0, 0.01, 0.10],
                },
                "curve": {
                    "points": points,
                    "p_grid": [0.0, 0.01, 0.10],
                    "P_ideal": 0.75,
                },
            }
        ),
        encoding="utf-8",
    )
    regimes_path = tmp_path / "regimes.json"
    regimes_path.write_text(
        json.dumps(
            {
                "schema_version": "2.0",
                "regimes": [
                    {
                        "label": "regime documentato",
                        "p_L": 0.02,
                        "source": "fixture esplicita del test",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return m8_path, regimes_path


def test_logical_figure_uses_explicit_inputs_and_outputs(tmp_path):
    m8_path, regimes_path = _write_inputs(tmp_path)
    output = tmp_path / "logical"
    pdf, png = gen_shor_logico.main(
        [
            "--input",
            str(m8_path),
            "--regimes",
            str(regimes_path),
            "--output-base",
            str(output),
        ]
    )
    assert pdf == output.with_suffix(".pdf") and pdf.is_file()
    assert png == output.with_suffix(".png") and png.is_file()


def test_logical_figure_can_omit_unjustified_qec_regimes(tmp_path):
    m8_path, _ = _write_inputs(tmp_path)
    output = tmp_path / "logical-no-regimes"
    pdf, png = gen_shor_logico.main(
        ["--input", str(m8_path), "--output-base", str(output)]
    )
    assert pdf.is_file() and png.is_file()


def test_cumulative_figure_has_no_hardcoded_probability_fallback(tmp_path):
    m8_path, _ = _write_inputs(tmp_path)
    output = tmp_path / "cumulative"
    pdf, png = gen_shor_pk.main(
        [
            "--input",
            str(m8_path),
            "--p-values",
            "0",
            "0.1",
            "--output-base",
            str(output),
        ]
    )
    assert pdf.is_file() and png.is_file()
    with pytest.raises(ValueError, match="non e' un punto M8 esatto"):
        gen_shor_pk.select_points(gen_shor_logico.load_m8_results(m8_path)[1], [0.05])


def test_figure_parsers_require_input_and_output_paths():
    with pytest.raises(SystemExit):
        gen_shor_logico.build_parser().parse_args([])
    with pytest.raises(SystemExit):
        gen_shor_pk.build_parser().parse_args([])
