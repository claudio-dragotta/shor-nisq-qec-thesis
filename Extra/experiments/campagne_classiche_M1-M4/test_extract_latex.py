import json
from copy import deepcopy

import numpy as np
import pytest
from scipy.stats import wilcoxon

import extract_latex


MANIFEST = {
    "circuit_revision": "shor-qpe-v2-amod15-correct",
    "noise_model_revision": "uniform-rz-virtual-v2",
    "postprocess_revision": "continued-fraction-v2",
    "circuit_sha256": "abc123",
    "basis_gates": ["rz", "sx", "x", "cx"],
    "optimization_level": 2,
    "seed_transpiler": 7,
}


def _wilcoxon(first, second, alternative="greater"):
    if list(first) == list(second):
        return 0.0, 1.0
    result = wilcoxon(
        first,
        second,
        alternative=alternative,
        zero_method="pratt",
        method="auto",
    )
    return float(result.statistic), float(result.pvalue)


def _holm(tests):
    ordered = sorted(tests.items(), key=lambda item: item[1]["p"])
    running = 0.0
    total = len(ordered)
    for index, (_, test) in enumerate(ordered):
        running = max(running, min(1.0, (total - index) * float(test["p"])))
        test["p_holm"] = running
    return tests


def _summary(iterations=(1,), *, sentinel=10, pair_ids=None):
    iterations = list(iterations)
    if pair_ids is None:
        pair_ids = list(range(len(iterations)))
    return {
        "M_bar": float(np.mean(iterations)),
        "std": float(np.std(iterations)),
        "success_rate": 1.0,
        "n_runs": len(iterations),
        "all_iters": iterations,
        "all_success": [True] * len(iterations),
        "failure_sentinel": sentinel,
        "pair_ids": list(pair_ids),
    }


def _paired_result(m1=(2, 2, 2), topk=(1, 1, 1), *, sentinel=10):
    pair_ids = list(range(len(m1)))
    m1_summary = _summary(m1, sentinel=sentinel, pair_ids=pair_ids)
    topk_summary = _summary(topk, sentinel=sentinel, pair_ids=pair_ids)
    statistic, p_value = _wilcoxon(m1, topk)
    return {
        "m1": m1_summary,
        "topk": topk_summary,
        "rho": m1_summary["M_bar"] / topk_summary["M_bar"],
        "pairing": {
            "paired": True,
            "unit": "replicate_seed_and_condition",
            "same_histograms_within_replica": True,
            "n_pairs": len(pair_ids),
            "failure_sentinel": sentinel,
            "pair_ids": pair_ids,
        },
        "wilcoxon_M1_gt_TOPK": {
            "W": statistic,
            "p": p_value,
            "alternative": "greater",
            "zero_method": "pratt",
        },
    }


def _campaign_item(m1, top4, m2, *, use_case="UC1", sentinel=20):
    def aggregate(values):
        return {"P_succ": 1.0, "M_bar": float(np.mean(values))}

    w_top, p_top = _wilcoxon(m1, top4, "greater")
    w_m2, p_m2 = _wilcoxon(m1, m2, "greater")
    w_ablation, p_ablation = _wilcoxon(top4, m2, "two-sided")
    tests = _holm(
        {
            "wilcoxon_M1_gt_TOP4": {
                "W": w_top,
                "p": p_top,
                "alternative": "greater",
            },
            "wilcoxon_M2_vs_TOP4": {
                "W": w_ablation,
                "p": p_ablation,
                "alternative": "two-sided",
            },
            "wilcoxon_M1_gt_M2": {
                "W": w_m2,
                "p": p_m2,
                "alternative": "greater",
            },
        }
    )
    return {
        "use_case": use_case,
        "M1": aggregate(m1),
        "M_TOP4": aggregate(top4),
        "M2": aggregate(m2),
        "rho_TOP4": float(np.mean(m1) / np.mean(top4)),
        "rho_M2": float(np.mean(m1) / np.mean(m2)),
        **tests,
        "multiplicity": {
            "method": "Holm",
            "family": [
                "wilcoxon_M1_gt_TOP4",
                "wilcoxon_M2_vs_TOP4",
                "wilcoxon_M1_gt_M2",
            ],
            "alpha": 0.05,
        },
        "_iterazioni": {"M1": list(m1), "M_TOP4": list(top4), "M2": list(m2)},
        "failure_sentinel": sentinel,
    }


def _zne_payload(iterations=None):
    iterations = iterations or {
        "M1": [3] * 12,
        "ZNE-2": [2] * 12,
        "ZNE-3": [3] * 12,
        "TOP4": [1] * 12,
    }
    strategies = {
        name: {**_summary(values, sentinel=10), "shots_mean": 32.0}
        for name, values in iterations.items()
    }
    comparisons = {}
    for name in ("ZNE-2", "ZNE-3", "TOP4"):
        statistic, p_value = _wilcoxon(iterations["M1"], iterations[name])
        comparisons[name] = {
            "W": statistic,
            "p": p_value,
            "alternative": "greater",
        }
    _holm(comparisons)
    return {
        "schema_version": "2.0",
        "analysis_revision": extract_latex.ZNE_ANALYSIS_REVISION,
        "timestamp": "fixed",
        "manifest": MANIFEST,
        "config": {"SHOTS": 32},
        "strategies": strategies,
        "comparisons_vs_M1": comparisons,
        "multiplicity": {"method": "Holm", "alpha": 0.05},
    }


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _source(payload, kind):
    return extract_latex.Source(
        kind=kind,
        path=extract_latex.Path(f"{kind}.json"),
        payload=payload,
        legacy=False,
        sha256="test",
    )


def test_v2_inputs_merge_and_render_all_requested_sections(tmp_path, capsys):
    baseline_m1 = _summary()
    parameter_k = _write(
        tmp_path / "parameter-k.json",
        {
            "schema_version": "2.0",
            "analysis_revision": extract_latex.PARAMETER_ANALYSIS_REVISION,
            "timestamp": "fixed",
            "manifest": MANIFEST,
            "baseline_m1": baseline_m1,
            "sweeps": {"sweep_k": {"1": _paired_result((1,), (1,))}},
        },
    )
    parameter_opt = _write(
        tmp_path / "parameter-opt.json",
        {
            "schema_version": "2.0",
            "analysis_revision": extract_latex.PARAMETER_ANALYSIS_REVISION,
            "timestamp": "fixed",
            "manifest": MANIFEST,
            "baseline_m1": baseline_m1,
            "sweeps": {
                "sweep_opt_level": {
                    "2": {**_paired_result((1,), (1,)), "cx_count": 10, "depth": 20}
                }
            },
        },
    )
    campaign_item = _campaign_item([1], [1], [1])
    baseline = _write(
        tmp_path / "baseline.json",
        {
            "schema_version": "2.0",
            "analysis_revision": extract_latex.BASELINE_ANALYSIS_REVISION,
            "timestamp": "fixed",
            "manifest": MANIFEST,
            "use_case": [campaign_item],
        },
    )
    zne = _write(tmp_path / "zne.json", _zne_payload({name: [1] for name in ("M1", "ZNE-2", "ZNE-3", "TOP4")}))

    result = extract_latex.main(
        [
            "--parameter-json",
            str(parameter_k),
            str(parameter_opt),
            "--baseline-json",
            str(baseline),
            "--zne-json",
            str(zne),
        ]
    )

    output = capsys.readouterr().out
    assert result == 0
    assert "% tabella sweep_k" in output
    assert "% tabella sweep_opt_level" in output
    assert "% tabella riepilogo_rho" in output
    assert "% tabella confronto_zne" in output
    assert "M2 vs M_TOP4 (Wilcoxon bilaterale)" in output
    assert "circuit_revision=shor-qpe-v2-amod15-correct" in output
    assert "sha256=" in output


def test_all_modern_parameter_sweeps_render_the_paired_contract():
    pair = _paired_result()
    sweeps = {
        "sweep_k": {"1": _paired_result((1,), (1,))},
        "sweep_eps2q": {
            "0.01": {**deepcopy(pair), "p_no_nonidentity_2q_proxy": 0.25}
        },
        "sweep_shots": {"1024": deepcopy(pair)},
        "sweep_joint": {
            "2": {"0.01": _summary(), "0.02": _summary()},
            "4": {"0.01": _summary(), "0.02": _summary()},
        },
        "sweep_t1t2": {"100000": {**deepcopy(pair), "t2_ns": 80000}},
        "sweep_eps1q": {"0.001": deepcopy(pair)},
        "sweep_pro": {"0.02": deepcopy(pair)},
        "sweep_opt_level": {
            "2": {**deepcopy(pair), "cx_count": 10, "depth": 20}
        },
    }
    output = "\n".join(extract_latex.render_parameter_sweeps(sweeps, _summary()))
    for name in sweeps:
        assert f"% tabella {name}" in output
    assert "P_no_nonidentity_2q_proxy" in output
    assert "rho & p" in output


def test_historical_schema_is_rejected_without_explicit_flag(tmp_path):
    historical = _write(tmp_path / "historical.json", {"sweep_k": {"1": {}}})
    with pytest.raises(extract_latex.ExtractionError, match="--allow-legacy-schema"):
        extract_latex._load_source(historical, "parameter", allow_legacy=False)


def test_historical_schema_can_be_read_only_with_explicit_flag(tmp_path):
    historical = _write(tmp_path / "historical.json", {"sweep_k": {"1": {}}})
    source = extract_latex._load_source(historical, "parameter", allow_legacy=True)
    sweeps, baseline = extract_latex._parameter_parts(source)
    assert source.legacy is True
    assert list(sweeps) == ["sweep_k"]
    assert baseline is None


def test_historical_extraction_is_end_to_end_opt_in(tmp_path, capsys):
    historical = _write(
        tmp_path / "historical.json",
        {
            "schema_version": "1.0",
            "sweep_k": {
                "1": {
                    "M_bar": 1.0,
                    "std": 0.0,
                    "success_rate": 1.0,
                    "all_iters": [1],
                }
            },
        },
    )
    assert extract_latex.main(
        ["--parameter-json", str(historical), "--allow-legacy-schema"]
    ) == 0
    output = capsys.readouterr().out
    assert "% ATTENZIONE: sorgente storica accettata esplicitamente." in output
    assert "% tabella sweep_k" in output


def test_future_schema_is_never_treated_as_legacy(tmp_path):
    future = _write(tmp_path / "future.json", {"schema_version": "3.0"})
    with pytest.raises(extract_latex.ExtractionError, match="non supportata"):
        extract_latex._load_source(future, "parameter", allow_legacy=True)


def test_v2_requires_semantic_manifest_and_exact_analysis_revision(tmp_path):
    payload = {
        "schema_version": "2.0",
        "analysis_revision": extract_latex.PARAMETER_ANALYSIS_REVISION,
        "manifest": {key: value for key, value in MANIFEST.items() if key != "postprocess_revision"},
    }
    path = _write(tmp_path / "bad-manifest.json", payload)
    with pytest.raises(extract_latex.ExtractionError, match="postprocess_revision"):
        extract_latex._load_source(path, "parameter", allow_legacy=False)

    payload["manifest"] = MANIFEST
    payload["analysis_revision"] = "old-simple-v2"
    path = _write(tmp_path / "bad-revision.json", payload)
    with pytest.raises(extract_latex.ExtractionError, match="contratto obsoleto"):
        extract_latex._load_source(path, "parameter", allow_legacy=False)


def test_failure_sentinel_and_finite_samples_are_enforced():
    summary = {
        "all_iters": [1, 4, 2, 4],
        "all_success": [True, False, True, False],
        "failure_sentinel": 4,
    }
    assert extract_latex._iterations(summary, "test") == [1.0, 4.0, 2.0, 4.0]
    with pytest.raises(extract_latex.ExtractionError, match="finiti"):
        extract_latex._iterations({"all_iters": [1, float("nan")]}, "test")

    with pytest.raises(extract_latex.ExtractionError, match="failure_sentinel incompatibili"):
        extract_latex._paired_greater(
            {"all_iters": [2, 2], "failure_sentinel": 3},
            {"all_iters": [1, 1], "failure_sentinel": 4},
            "paired",
        )


def test_paired_contract_rejects_permuted_or_missing_pair_ids():
    pair = _paired_result()
    pair["topk"]["pair_ids"] = list(reversed(pair["topk"]["pair_ids"]))
    with pytest.raises(extract_latex.ExtractionError, match="pair_ids"):
        extract_latex._paired_components(pair, "condition")


def test_v2_eps_sweep_requires_new_nonidentity_proxy_key():
    pair = _paired_result()
    modern = {"0.01": {**pair, "p_no_nonidentity_2q_proxy": 0.25}}
    output = "\n".join(extract_latex._render_sweep_eps2q(modern, legacy=False))
    assert "P_no_nonidentity_2q_proxy" in output
    assert "$2.50e-01$" in output

    with pytest.raises(extract_latex.ExtractionError, match="p_no_nonidentity_2q_proxy"):
        extract_latex._render_sweep_eps2q(
            {"0.01": {**_paired_result(), "p_surv": 0.25}}, legacy=False
        )
    with pytest.raises(extract_latex.ExtractionError, match="deve essere numerico"):
        extract_latex._render_sweep_eps2q(
            {
                "0.01": {
                    **_paired_result(),
                    "p_no_nonidentity_2q_proxy": "not-a-number",
                }
            },
            legacy=False,
        )


def test_joint_grid_and_t2_must_be_explicit_and_consistent():
    with pytest.raises(extract_latex.ExtractionError, match="stessa griglia"):
        extract_latex._render_sweep_joint(
            {"2": {"0.01": _summary()}, "4": {"0.02": _summary()}}
        )
    with pytest.raises(extract_latex.ExtractionError, match="t2_ns esplicito"):
        extract_latex._render_sweep_t1t2(
            {"100000": _paired_result()}, None, legacy=False
        )


def test_baseline_uses_two_sided_m2_vs_top4_and_ties_equal_one():
    different = _campaign_item([3] * 20, [1] * 20, [4] * 20)
    assert different["wilcoxon_M2_vs_TOP4"]["p"] < 0.01
    assert different["wilcoxon_M2_vs_TOP4"]["p_holm"] < 0.01
    output = "\n".join(
        extract_latex.render_baseline(
            _source(
                {"schema_version": "2.0", "manifest": MANIFEST, "use_case": [different]},
                "baseline",
            )
        )
    )
    assert "M2 vs M_TOP4 (Wilcoxon bilaterale)" in output
    assert "wilcoxon_TOP4_gt_M2" not in output

    tied = _campaign_item([1] * 10, [1] * 10, [1] * 10)
    assert tied["wilcoxon_M2_vs_TOP4"]["p"] == 1.0
    assert tied["wilcoxon_M2_vs_TOP4"]["p_holm"] == 1.0
    extract_latex.render_baseline(
        _source({"schema_version": "2.0", "manifest": MANIFEST, "use_case": [tied]}, "baseline")
    )


def test_baseline_rejects_stale_raw_or_old_ablation_key():
    item = _campaign_item([3] * 10, [1] * 10, [2] * 10)
    item["wilcoxon_M1_gt_TOP4"]["p"] = 0.9
    with pytest.raises(extract_latex.ExtractionError, match="non coincide"):
        extract_latex.render_baseline(
            _source({"use_case": [item]}, "baseline")
        )

    item = _campaign_item([1] * 10, [1] * 10, [1] * 10)
    item["wilcoxon_TOP4_gt_M2"] = item.pop("wilcoxon_M2_vs_TOP4")
    with pytest.raises(extract_latex.ExtractionError, match="wilcoxon_M2_vs_TOP4"):
        extract_latex.render_baseline(_source({"use_case": [item]}, "baseline"))


def test_zne_recomputes_raw_wilcoxon_and_displays_holm():
    payload = _zne_payload()
    output = "\n".join(extract_latex.render_zne(_source(payload, "zne")))
    expected = extract_latex._p_text(
        payload["comparisons_vs_M1"]["ZNE-2"]["p_holm"], True
    )
    assert expected in output

    stale = deepcopy(payload)
    stale["comparisons_vs_M1"]["TOP4"]["p"] = 0.9
    with pytest.raises(extract_latex.ExtractionError, match="non coincidono"):
        extract_latex.render_zne(_source(stale, "zne"))

    old = deepcopy(payload)
    old.pop("comparisons_vs_M1")
    with pytest.raises(extract_latex.ExtractionError, match="comparisons_vs_M1"):
        extract_latex.render_zne(_source(old, "zne"))


def test_paired_wilcoxon_requires_equal_length():
    reference = {"all_iters": [4] * 10, "failure_sentinel": 4}
    candidate = {"all_iters": [1] * 10, "failure_sentinel": 4}
    assert extract_latex._paired_greater(reference, candidate, "paired") < 0.01
    with pytest.raises(extract_latex.ExtractionError, match="stessa lunghezza"):
        extract_latex._paired_greater(
            reference,
            {"all_iters": [1, 1], "failure_sentinel": 4},
            "paired",
        )
