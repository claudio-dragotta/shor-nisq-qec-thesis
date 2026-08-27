"""Regression tests for the scientific contract shared by M8 and M13."""
from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import shor_logico as m8  # noqa: E402
import topk_logico as m13  # noqa: E402


@pytest.mark.parametrize(
    ("num_qubits", "expected_lambda", "nonidentity_terms"),
    [(1, 4 * 0.12 / 3, 3), (2, 16 * 0.12 / 15, 15)],
)
def test_p_l_is_total_nonidentity_pauli_probability(
    num_qubits, expected_lambda, nonidentity_terms
):
    assert m8.depolarizing_lambda(0.12, num_qubits) == pytest.approx(expected_lambda)
    channel = m8.logical_pauli_error(0.12, num_qubits).to_dict()
    probabilities = channel["probabilities"]
    assert len(probabilities) == nonidentity_terms + 1
    assert probabilities[0] == pytest.approx(0.88)
    assert sum(probabilities[1:]) == pytest.approx(0.12)
    assert all(value == pytest.approx(probabilities[1]) for value in probabilities[1:])


def test_noise_manifest_forbids_direct_m6_m7_equivalence():
    manifest = m8.logical_noise_manifest()
    assert manifest["kind"] == "phenomenological_per_gate_proxy"
    assert manifest["aer_lambda"] == {"1q": "4*p_L/3", "2q": "16*p_L/15"}
    assert manifest["direct_equivalence_to_M6_M7"] is False


@pytest.mark.parametrize(
    "grid",
    [
        [0.1, 0.2],
        [0.0, 0.0, 0.1],
        [0.0, 0.2, 0.1],
        [0.0, -0.1],
        [0.0, 1.1],
        [0.0, float("nan")],
        [0.0],
    ],
)
def test_p_grid_rejects_missing_or_duplicate_zero_order_and_domain(grid):
    with pytest.raises(ValueError):
        m8.validate_p_grid(grid)


def test_p_grid_accepts_single_zero_and_strict_order():
    assert m8.validate_p_grid([0, 0.001, 0.5, 1]) == [0.0, 0.001, 0.5, 1.0]


def test_monotonicity_combines_uncertainty_from_both_points():
    compatible = m8.assess_monotonicity(
        [
            {"p_L": 0.0, "P_success": 0.50, "uncertainty_se": 0.10},
            {"p_L": 0.1, "P_success": 0.53, "uncertainty_se": 0.10},
        ]
    )
    comparison = compatible["comparisons"][0]
    assert comparison["combined_se"] == pytest.approx(math.sqrt(0.02))
    assert compatible["monotone_compatible"] is True

    incompatible = m8.assess_monotonicity(
        [
            {"p_L": 0.0, "P_success": 0.20, "uncertainty_se": 0.01},
            {"p_L": 0.1, "P_success": 0.80, "uncertainty_se": 0.01},
        ]
    )
    assert incompatible["monotone_compatible"] is False


class _FakeResult:
    def __init__(self, counts):
        self._counts = counts

    def result(self):
        return self

    def get_counts(self):
        return self._counts


class _FakeSimulator:
    def __init__(self, *args, **kwargs):
        pass

    def run(self, circuit, shots, seed_simulator):
        good = shots // 2
        return _FakeResult({"01000000": good, "00000000": shots - good})


def test_m8_saves_real_replica_outcomes_and_aggregated_wilson(monkeypatch):
    monkeypatch.setattr(m8, "AerSimulator", _FakeSimulator)
    point = m8.evaluate_point(object(), 15, 7, 8, 0.0, 10, 3, 42, 0)
    assert len(point["replicates"]) == 3
    assert [row["successes"] for row in point["replicates"]] == [5, 5, 5]
    assert point["successes"] == 15
    assert point["total_shots"] == 30
    assert point["P_success"] == pytest.approx(0.5)
    assert point["wilson_ci"]["low"] < 0.5 < point["wilson_ci"]["high"]


def test_m8_schema_v2_contains_manifests():
    args = SimpleNamespace(
        N=15,
        a=7,
        n_count=8,
        shots=10,
        replicates=2,
        seed=42,
        confidence=0.95,
    )
    curve = {"p_grid": [0.0, 0.1]}
    payload = m8.build_payload(args, curve)
    assert payload["schema_version"] == "2.0"
    assert payload["logical_noise_manifest"]["direct_equivalence_to_M6_M7"] is False
    assert payload["circuit_manifest"]["circuit_revision"]


def test_topk_tie_bounds_and_seeded_selection_are_reproducible():
    counts = {"000": 20, "001": 10, "010": 10, "011": 10}
    predicate = lambda bits: bits == "001"
    first = m13.resolve_top_k(counts, 2, 123, predicate)
    second = m13.resolve_top_k(counts, 2, 123, predicate)
    assert first == second
    assert first["lower_success"] is False
    assert first["upper_success"] is True
    assert first["lower_success"] <= first["seeded_success"] <= first["upper_success"]
    assert first["boundary"]["tie_present"] is True
    assert first["boundary"]["slots"] == 1


def test_topk_lower_bound_is_true_when_success_is_forced():
    counts = {"000": 20, "001": 10, "010": 10}
    result = m13.resolve_top_k(counts, 3, 123, lambda bits: bits == "001")
    assert result["lower_success"] is True
    assert result["seeded_success"] is True
    assert result["upper_success"] is True


def test_topk_reuses_one_histogram_and_saves_every_replica(monkeypatch):
    monkeypatch.setattr(m13, "AerSimulator", _FakeSimulator)
    point = m13.evaluate_point(object(), 0.0, 10, 3, 2, 42, 0, 0.95)
    assert len(point["replicates"]) == 3
    assert point["per_measure"]["successes"] == 15
    assert point["per_measure"]["total"] == 30
    for row in point["replicates"]:
        assert row["counts"] == {"00000000": 5, "01000000": 5}
        assert "lower_success" in row["topk"]
        assert "seeded_success" in row["top1"]


def test_equivalence_uses_prespecified_interval_not_point_estimate():
    first = {
        "estimate": 0.50,
        "wilson_ci": {"low": 0.45, "high": 0.55},
    }
    last = {
        "estimate": 0.48,
        "wilson_ci": {"low": 0.43, "high": 0.53},
    }
    wide = m13.equivalence_test(first, last, 0.20)
    narrow = m13.equivalence_test(first, last, 0.05)
    assert wide["equivalent"] is True
    assert narrow["equivalent"] is False
    assert wide["interval"]["method"].startswith("Newcombe")


def test_tie_robust_envelope_has_simultaneous_bonferroni_coverage():
    lower = m13._binary_summary([False] * 20 + [True] * 80, 0.95)
    upper = m13._binary_summary([False] * 10 + [True] * 90, 0.95)
    result = m13.tie_robust_equivalence(
        {"lower_bound": lower, "upper_bound": upper},
        {"lower_bound": lower, "upper_bound": upper},
        0.20,
        0.95,
    )
    envelope = result["identified_confidence_envelope"]
    assert envelope["component_confidence"] == pytest.approx(0.9875)
    assert envelope["method"].startswith("Bonferroni-adjusted Wilson")


def test_m13_default_has_at_least_200_replicates_and_static_analysis_plan():
    args = m13.build_parser().parse_args([])
    assert args.replicates >= 200
    plan = m13.analysis_plan(args.K, args.confidence, args.equivalence_margin)
    assert plan["primary_contrast"] == "p_L=0 minus largest preregistered p_L"
    assert plan["equivalence_margin_absolute"] == pytest.approx(0.10)


def test_m13_checkpoint_is_atomic_and_requires_exact_identity(tmp_path):
    path = tmp_path / "checkpoint.json"
    identity = {"p_grid": [0.0, 0.1], "seed": 42}
    points = [{"p_L": 0.0, "replicates": [{"counts": {"0": 10}}]}]
    m13._write_checkpoint(path, identity, points, "in_progress")

    assert not path.with_name(path.name + ".tmp").exists()
    assert m13._load_checkpoint(path, identity) == points

    with pytest.raises(ValueError, match="configurazione diversa"):
        m13._load_checkpoint(path, {"p_grid": [0.0, 0.2], "seed": 42})


def test_m13_checkpoint_rejects_nonprefix_points(tmp_path):
    path = tmp_path / "checkpoint.json"
    identity = {"p_grid": [0.0, 0.1], "seed": 42}
    m13._write_checkpoint(path, identity, [{"p_L": 0.1}], "in_progress")
    with pytest.raises(ValueError, match="prefisso valido"):
        m13._load_checkpoint(path, identity)
