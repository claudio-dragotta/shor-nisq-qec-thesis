"""Test non-Aer per i diagnostici attivi della Fase 1."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

import analisi_moda_uc1 as mode_diagnostic
import causa_bilanciamento_dataset as historical_balance
import frazione_coerente_efficace as fraction_diagnostic


FIGURE_SCRIPT = Path(__file__).resolve().parents[3] / "figure_src" / "gen_audit_classificatore.py"


def _load_figure_module():
    spec = importlib.util.spec_from_file_location("gen_audit_classificatore_v2", FIGURE_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _manifest() -> dict:
    return {
        "circuit_revision": "test-circuit-v2",
        "noise_model_revision": "test-noise-v2",
        "postprocess_revision": "test-ranking-v2",
        "circuit_sha256": "a" * 64,
        "basis_gates": ["rz", "sx", "x", "cx"],
        "optimization_level": 2,
        "seed_transpiler": 20260819,
    }


def _audit(manifest: dict, use_case: str, top_k: int, positive: int, negative: int, eps: float) -> dict:
    return {
        "schema_version": "2.0",
        "manifest": manifest,
        "use_case": use_case,
        "label_top_k": top_k,
        "class_balance": {"positive": positive, "negative": negative},
        "noise_base": {"eps_2q": eps},
    }


def test_mode_analysis_uses_v2_ranking_and_records_full_histogram() -> None:
    record = mode_diagnostic.analyse_counts(
        {"00000000": 10, "01000000": 9, "10000000": 7, "11000000": 6},
        tie_seed=123,
    )

    assert record["top_value"] == 0
    assert record["mode_is_zero"] is True
    assert record["mode_factor_success"] is False
    assert record["top4_factor_success"] is True
    assert len(record["histogram_counts"]) == 256
    assert sum(record["histogram_counts"]) == 32


def test_effective_fraction_and_qiskit_depolarizing_proxy() -> None:
    peak_mass = 0.75
    expected_fraction = (peak_mass - 4 / 256) / (1 - 4 / 256)
    assert fraction_diagnostic.effective_signal_fraction(
        peak_mass, n_peaks=4, n_cells=256
    ) == pytest.approx(expected_fraction)

    observed = fraction_diagnostic.p_no_nonidentity_2q_proxy(0.01, 224)
    assert observed == pytest.approx((1 - 15 * 0.01 / 16) ** 224)


def test_seed_schedule_is_disjoint_and_rejects_aer_overflow() -> None:
    assert mode_diagnostic.simulation_seeds(7, 3) == [7_010_000, 7_020_000, 7_030_000]
    with pytest.raises(ValueError, match="massimo seed Aer"):
        fraction_diagnostic.simulation_seeds(2148, 1)


class _FakeResult:
    def __init__(self, counts: dict[str, int]):
        self._counts = counts

    def result(self):
        return self

    def get_counts(self) -> dict[str, int]:
        return self._counts


class _FakeSimulator:
    def __init__(self, counts: dict[str, int]):
        self._counts = counts

    def run(self, *args, **kwargs):
        return _FakeResult(self._counts)


def test_mode_payload_is_schema2_with_manifest_without_aer(monkeypatch) -> None:
    monkeypatch.setattr(mode_diagnostic, "compile_shor_circuit", lambda *args: object())
    monkeypatch.setattr(mode_diagnostic, "build_noise_model", lambda **kwargs: object())
    monkeypatch.setattr(mode_diagnostic, "experiment_manifest", lambda *args: _manifest())
    monkeypatch.setattr(
        mode_diagnostic,
        "AerSimulator",
        lambda **kwargs: _FakeSimulator(
            {"00000000": 10, "01000000": 9, "10000000": 7, "11000000": 6}
        ),
    )

    payload = mode_diagnostic.run_diagnostic(seed=1, shots=32, reps=1)

    assert payload["schema_version"] == "2.0"
    assert payload["manifest"] == _manifest()
    assert payload["representative_mode_zero"]["histogram_counts"][0] == 10


def test_fraction_payload_uses_proxy_field_without_aer(monkeypatch) -> None:
    class FakeCircuit:
        @staticmethod
        def count_ops():
            return {"cx": 224}

    monkeypatch.setattr(
        fraction_diagnostic, "compile_shor_circuit", lambda *args: FakeCircuit()
    )
    monkeypatch.setattr(fraction_diagnostic, "build_noise_model", lambda **kwargs: object())
    monkeypatch.setattr(
        fraction_diagnostic, "experiment_manifest", lambda *args: _manifest()
    )
    monkeypatch.setattr(
        fraction_diagnostic,
        "AerSimulator",
        lambda **kwargs: _FakeSimulator(
            {"00000000": 8, "01000000": 8, "10000000": 8, "11000000": 8}
        ),
    )

    payload = fraction_diagnostic.run_diagnostic(
        seed=1, shots=32, reps=1, lambdas_2q=[0.01]
    )

    row = payload["results"][0]
    assert payload["schema_version"] == "2.0"
    assert payload["manifest"] == _manifest()
    assert row["p_no_nonidentity_2q_proxy"] == pytest.approx(
        (1 - 15 * 0.01 / 16) ** 224
    )
    assert all("surv" not in key.lower() for key in row)


def test_historical_balance_diagnostic_is_a_non_aer_stub(capsys) -> None:
    assert historical_balance.main([]) == 2
    assert "DISABILITATO" in capsys.readouterr().err
    assert not hasattr(historical_balance, "AerSimulator")


def test_figure_generator_requires_schema_v2(tmp_path: Path) -> None:
    module = _load_figure_module()
    historical = tmp_path / "historical.json"
    historical.write_text(json.dumps({"schema_version": "1.0"}), encoding="utf-8")

    with pytest.raises(module.ArtifactError, match="richiesto esclusivamente '2.0'"):
        module.load_v2_json(historical, label="storico")


def test_figure_generator_smoke_from_explicit_json_only(tmp_path: Path) -> None:
    module = _load_figure_module()
    manifest = _manifest()
    counts = [0] * 256
    counts[0], counts[64], counts[128], counts[192] = 10, 9, 7, 6
    ordered = [
        {"rank": 1, "value": 0, "factor_success": False},
        {"rank": 2, "value": 64, "factor_success": True},
        {"rank": 3, "value": 128, "factor_success": True},
        {"rank": 4, "value": 192, "factor_success": True},
    ]
    mode = {
        "schema_version": "2.0",
        "artifact_type": module.MODE_ARTIFACT,
        "manifest": manifest,
        "config": {"N": 15, "a": 7, "n_count": 8, "use_case": "UC1"},
        "reference": {
            "theoretical_peaks": [0, 64, 128, 192],
            "useful_theoretical_peaks": [64, 128, 192],
            "factorable_outcomes": [64, 128, 192],
            "factorable_outcome_count": 3,
        },
        "representative_mode_zero": {
            "rep": 1,
            "seed_simulator": 7_010_000,
            "histogram_counts": counts,
            "ordered_top4": ordered,
        },
    }
    fraction = {
        "schema_version": "2.0",
        "artifact_type": module.FRACTION_ARTIFACT,
        "manifest": manifest,
        "circuit": {"n_cx": 224},
        "results": [
            {
                "lambda_2q": 0.01,
                "effective_signal_fraction": 0.7,
                "p_no_nonidentity_2q_proxy": (1 - 15 * 0.01 / 16) ** 224,
            },
            {
                "lambda_2q": 0.05,
                "effective_signal_fraction": 0.3,
                "p_no_nonidentity_2q_proxy": (1 - 15 * 0.05 / 16) ** 224,
            },
        ],
    }
    training = {
        "schema_version": "2.0",
        "manifest": manifest,
        "outcomes": {
            "UC1": {
                "1": _audit(manifest, "UC1", 1, 7, 3, 0.01),
                "16": _audit(manifest, "UC1", 16, 10, 0, 0.01),
            },
            "UC2": {
                "1": _audit(manifest, "UC2", 1, 5, 5, 0.05),
                "16": _audit(manifest, "UC2", 16, 9, 1, 0.05),
            },
        },
    }
    mode_path = tmp_path / "mode.json"
    fraction_path = tmp_path / "fraction.json"
    training_path = tmp_path / "training.json"
    mode_path.write_text(json.dumps(mode), encoding="utf-8")
    fraction_path.write_text(json.dumps(fraction), encoding="utf-8")
    training_path.write_text(json.dumps(training), encoding="utf-8")
    output_dir = tmp_path / "figures"

    result = module.generate_all(
        mode_json=mode_path,
        fraction_json=fraction_path,
        training_json=training_path,
        output_dir=output_dir,
    )

    assert Path(result["provenance_path"]).is_file()
    for name in (
        "audit_istogramma_negativo",
        "frazione_coerente",
        "tetto_classe_negativa",
    ):
        assert (output_dir / f"{name}.pdf").is_file()
        assert (output_dir / f"{name}.png").is_file()
