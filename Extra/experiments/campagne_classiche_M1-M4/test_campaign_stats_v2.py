"""Regressioni statistiche per il contratto delle campagne v2."""

import json
import sys

import numpy as np
import pytest

import train_classifier
import run_top4_baseline
import run_parameter_analysis
import run_zne_comparison
from rerun_baseline_corretto import statistiche
from run_parameter_analysis import summarize as summarize_parameter
from run_top4_baseline import paired_greater
from run_zne_comparison import summarize as summarize_zne


def test_success_at_last_iteration_is_not_confused_with_failure() -> None:
    # 50 = successo all'ultima iterazione; 51 = sentinel del fallimento.
    encoded = np.array([50, 51])
    result = statistiche(
        'UC-test', encoded, encoded, None,
        k=2, shots=32, max_iter=50,
    )

    assert result['M1']['n_succ'] == 1
    assert result['M1']['P_succ'] == pytest.approx(0.5)
    assert result['M1']['M_bar'] == pytest.approx(50.0)
    assert result['M1']['mean_budget_used'] == pytest.approx(50.0)


def test_parameter_summary_preserves_censoring_and_reports_uncertainty() -> None:
    summary = summarize_parameter([
        {'iterations': 50, 'success': True},
        {'iterations': 50, 'success': False},
    ])

    assert summary['all_iters'] == [50, 51]
    assert summary['all_success'] == [True, False]
    assert summary['success_rate'] == pytest.approx(0.5)
    low, high = summary['success_rate_wilson95']
    assert 0 <= low < 0.5 < high <= 1


def test_parameter_summary_uses_the_run_specific_failure_sentinel() -> None:
    summary = summarize_parameter([
        {'iterations': 3, 'success': True, 'failure_sentinel': 4, 'pair_id': 10},
        {'iterations': 3, 'success': False, 'failure_sentinel': 4, 'pair_id': 11},
    ])

    assert summary['all_iters'] == [3, 4]
    assert summary['failure_sentinel'] == 4
    assert summary['pair_ids'] == [10, 11]


def test_zne_summary_uses_failure_sentinel_but_real_consumed_budget() -> None:
    summary = summarize_zne([
        {'iterations': 50, 'success': True, 'shots_used': 1600},
        {'iterations': 50, 'success': False, 'shots_used': 1600},
    ])

    assert summary['all_iters'] == [50, 51]
    assert summary['mean_budget_used'] == pytest.approx(50.0)
    assert summary['mean_shots_used_all'] == pytest.approx(1600.0)


def test_paired_test_handles_complete_ties_without_scipy_error() -> None:
    statistic, p_value = paired_greater([1, 1, 2], [1, 1, 2])
    assert statistic == 0
    assert p_value == 1


def test_baseline_ablation_is_two_sided_holm_and_handles_ties() -> None:
    different = statistiche(
        'UC-test',
        np.array([3] * 20),
        np.array([1] * 20),
        np.array([4] * 20),
        k=20,
        shots=32,
        max_iter=10,
    )
    assert 'wilcoxon_TOP4_gt_M2' not in different
    ablation = different['wilcoxon_M2_vs_TOP4']
    assert ablation['alternative'] == 'two-sided'
    assert ablation['p'] < 0.01
    assert ablation['p'] <= ablation['p_holm'] < 0.01
    assert different['multiplicity']['method'] == 'Holm'

    tied = statistiche(
        'UC-tie',
        np.ones(10, dtype=int),
        np.ones(10, dtype=int),
        np.ones(10, dtype=int),
        k=10,
        shots=32,
        max_iter=10,
    )
    assert tied['wilcoxon_M2_vs_TOP4']['p'] == 1.0
    assert tied['wilcoxon_M2_vs_TOP4']['p_holm'] == 1.0


def test_training_audit_records_the_sampling_width(monkeypatch, tmp_path) -> None:
    def fake_dataset(*args, noise_factor, **kwargs):
        assert noise_factor == pytest.approx(0.25)
        return np.zeros((10, 256)), {16: np.ones(10, dtype=int)}

    monkeypatch.setattr(train_classifier, 'generate_dataset', fake_dataset)
    monkeypatch.setattr(train_classifier, 'experiment_manifest', lambda *args: {})

    result = train_classifier.train_and_save(
        'UC-test', 15, 7, 8, {}, n_samples=10, shots=1, seed=3,
        output_dir=tmp_path, label_top_ks=(16,), noise_factor=0.25,
    )

    audit_path = tmp_path / 'top16' / 'label_audit_UC-test.json'
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    assert result[16]['noise_sampling']['relative_half_width'] == 0.25
    assert audit['noise_sampling']['relative_half_width'] == 0.25


def test_training_checkpoint_roundtrip_is_atomic_and_strict(tmp_path) -> None:
    checkpoint = tmp_path / 'dataset.npz'
    contract = {
        'checkpoint_revision': train_classifier.CHECKPOINT_REVISION,
        'n_count': 2,
        'n_samples': 3,
        'label_top_ks': [1, 2],
    }
    features = np.asarray([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
    ])
    labels = {1: [1, 0], 2: [1, 1]}

    train_classifier._save_dataset_checkpoint(
        checkpoint, contract, features, labels
    )
    restored_features, restored_labels = train_classifier._load_dataset_checkpoint(
        checkpoint, contract
    )

    assert checkpoint.is_file()
    assert not checkpoint.with_suffix('.npz.tmp').exists()
    assert restored_features == pytest.approx(features)
    assert restored_labels[1].tolist() == [1, 0]
    assert restored_labels[2].tolist() == [1, 1]

    incompatible = {**contract, 'n_samples': 4}
    with pytest.raises(ValueError, match='Checkpoint incompatibile'):
        train_classifier._load_dataset_checkpoint(checkpoint, incompatible)


def test_baseline_strategies_share_each_simulated_histogram(monkeypatch) -> None:
    class FakeResult:
        def __init__(self, counts):
            self._counts = counts

        def result(self):
            return self

        def get_counts(self):
            return self._counts

    class FakeSimulator:
        def __init__(self):
            self.calls = 0

        def run(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return FakeResult({'00000000': 10, '01000000': 9})
            return FakeResult({'01000000': 10, '00000000': 9})

    simulator = FakeSimulator()
    monkeypatch.setattr(run_top4_baseline, 'build_noise_model', lambda **kw: object())
    monkeypatch.setattr(run_top4_baseline, 'compile_shor_circuit', lambda *a: object())
    monkeypatch.setattr(
        run_top4_baseline, 'AerSimulator', lambda **kw: simulator
    )

    m1, top4, m2 = run_top4_baseline.run_uc(
        'UC-test', 15, 7, 8, {}, with_m2=False,
        k=1, shots=32, max_iter=3,
    )

    assert m1.tolist() == [2]
    assert top4.tolist() == [1]
    assert m2 is None
    assert simulator.calls == 2


def test_parameter_run_topks_shares_one_histogram_for_every_k(monkeypatch) -> None:
    class FakeResult:
        def __init__(self, counts):
            self._counts = counts

        def result(self):
            return self

        def get_counts(self):
            return self._counts

    class FakeSimulator:
        def __init__(self):
            self.calls = []

        def run(self, circuit, *, shots, seed_simulator):
            self.calls.append((circuit, shots, seed_simulator))
            if len(self.calls) == 1:
                return FakeResult({'00000000': 10, '00000001': 9})
            return FakeResult({'00000001': 10, '00000000': 9})

    simulator = FakeSimulator()
    monkeypatch.setattr(
        run_parameter_analysis, 'AerSimulator', lambda **kwargs: simulator
    )
    monkeypatch.setattr(
        run_parameter_analysis,
        'rank_measurements',
        lambda counts, seed: list(counts.items()),
    )
    monkeypatch.setattr(
        run_parameter_analysis,
        'extract_factors',
        lambda measured, *args: ((3, 5) if measured == 1 else (None, None)),
    )

    outcomes = run_parameter_analysis.run_topks(
        15, 7, 8, object(), shots=19, max_iter=3, seed=7,
        top_ks=(1, 2, 4), compiled_circuit=object(),
    )

    assert len(simulator.calls) == 2
    assert outcomes[1]['iterations'] == 2
    assert outcomes[2]['iterations'] == 1
    assert outcomes[4]['iterations'] == 1
    assert {outcome['pair_id'] for outcome in outcomes.values()} == {7}
    assert {outcome['failure_sentinel'] for outcome in outcomes.values()} == {4}


@pytest.mark.parametrize('invalid', [(1.5,), (True,), (0,), (257,)])
def test_parameter_run_topks_rejects_invalid_k_without_truncation(invalid) -> None:
    with pytest.raises(ValueError, match='top_ks'):
        run_parameter_analysis.run_topks(
            15, 7, 8, object(), top_ks=invalid, compiled_circuit=object()
        )


def _fake_grid_outcomes(*args, seed, top_ks, max_iter, **kwargs):
    outcomes = {}
    for top_k in top_ks:
        outcomes[int(top_k)] = {
            'iterations': 2 if int(top_k) == 1 else 1,
            'success': True,
            'failure_sentinel': max_iter + 1,
            'pair_id': seed,
        }
    return outcomes


@pytest.mark.parametrize(
    'function_name, expected_conditions',
    [
        ('sweep_eps2q', 6),
        ('sweep_shots', 5),
        ('sweep_t1t2', 5),
        ('sweep_eps1q', 6),
        ('sweep_pro', 6),
        ('sweep_opt_level', 4),
    ],
)
def test_each_condition_saves_a_verified_m1_topk_pair(
    monkeypatch, capsys, function_name, expected_conditions
) -> None:
    class FakeCircuit:
        def count_ops(self):
            return {'cx': 10}

        def depth(self):
            return 20

    calls = []

    def fake_run(*args, **kwargs):
        calls.append(tuple(kwargs['top_ks']))
        return _fake_grid_outcomes(*args, **kwargs)

    monkeypatch.setattr(run_parameter_analysis, 'K_REPS', 3)
    monkeypatch.setattr(run_parameter_analysis, 'build_noise_model', lambda **kw: object())
    monkeypatch.setattr(run_parameter_analysis, 'compile_shor_circuit', lambda *a, **kw: FakeCircuit())
    monkeypatch.setattr(run_parameter_analysis, 'run_topks', fake_run)

    results = getattr(run_parameter_analysis, function_name)()
    capsys.readouterr()

    assert len(results) == expected_conditions
    assert len(calls) == expected_conditions * 3
    assert all(call == (1, 4) for call in calls)
    for condition in results.values():
        assert condition['pairing']['paired'] is True
        assert condition['pairing']['same_histograms_within_replica'] is True
        assert condition['pairing']['pair_ids'] == [0, 1, 2]
        assert condition['m1']['pair_ids'] == condition['topk']['pair_ids']
        assert condition['rho'] == pytest.approx(2.0)
        assert condition['wilcoxon_M1_gt_TOPK']['alternative'] == 'greater'


@pytest.mark.parametrize(
    'function_name, expected_calls, expected_grid',
    [
        ('sweep_k', 3, (1, 2, 3, 4, 6, 8)),
        ('sweep_joint', 12, (2, 4, 6, 8)),
    ],
)
def test_k_and_joint_sweeps_reuse_each_k_grid(
    monkeypatch, capsys, function_name, expected_calls, expected_grid
) -> None:
    calls = []

    def fake_run(*args, **kwargs):
        calls.append(tuple(kwargs['top_ks']))
        return _fake_grid_outcomes(*args, **kwargs)

    monkeypatch.setattr(run_parameter_analysis, 'K_REPS', 3)
    monkeypatch.setattr(run_parameter_analysis, 'M1_UC1_ITERS', [2, 2, 2])
    monkeypatch.setattr(run_parameter_analysis, 'M1_UC1_MBAR', 2.0)
    monkeypatch.setattr(run_parameter_analysis, 'build_noise_model', lambda **kw: object())
    monkeypatch.setattr(run_parameter_analysis, 'run_topks', fake_run)

    results = getattr(run_parameter_analysis, function_name)()
    capsys.readouterr()

    assert len(calls) == expected_calls
    assert all(call == expected_grid for call in calls)
    if function_name == 'sweep_k':
        for pair in results.values():
            assert pair['pairing']['same_histograms_within_replica'] is True
            assert pair['m1']['pair_ids'] == pair['topk']['pair_ids'] == [0, 1, 2]
        assert results[1]['rho'] == pytest.approx(1.0)
        assert results[1]['wilcoxon_M1_gt_TOPK']['p'] == pytest.approx(1.0)
        assert results[4]['rho'] == pytest.approx(2.0)


def test_parameter_main_writes_the_shared_histogram_revision(
    monkeypatch, tmp_path
) -> None:
    m1_runs = [
        {
            'iterations': 2,
            'success': True,
            'failure_sentinel': 4,
            'pair_id': pair_id,
        }
        for pair_id in (0, 1)
    ]
    topk_runs = [
        {
            'iterations': 1,
            'success': True,
            'failure_sentinel': 4,
            'pair_id': pair_id,
        }
        for pair_id in (0, 1)
    ]
    pair = run_parameter_analysis.summarize_pair(m1_runs, topk_runs)
    baseline = run_parameter_analysis.summarize(m1_runs)
    monkeypatch.setattr(run_parameter_analysis, 'K_REPS', 2)
    monkeypatch.setattr(run_parameter_analysis, 'MAX_ITER', 3)
    monkeypatch.setattr(run_parameter_analysis, 'DEFAULT_SHOTS', 16)
    monkeypatch.setattr(run_parameter_analysis, 'prepare_m1_reference', lambda: baseline)
    monkeypatch.setattr(run_parameter_analysis, 'sweep_shots', lambda: {128: pair})
    monkeypatch.setattr(
        run_parameter_analysis,
        'experiment_manifest',
        lambda: {'postprocess_revision': 'test'},
    )
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'run_parameter_analysis.py',
            '--sweep',
            'shots',
            '--k-reps',
            '2',
            '--max-iter',
            '3',
            '--shots',
            '16',
            '--output-dir',
            str(tmp_path),
        ],
    )

    run_parameter_analysis.main()

    output = next(tmp_path.glob('results_parameter_analysis_v2_*.json'))
    payload = json.loads(output.read_text(encoding='utf-8'))
    assert payload['schema_version'] == '2.0'
    assert payload['analysis_revision'] == 'parameter-analysis-shared-hist-v4'
    assert 'same histogram' in payload['config']['pairing_unit']
    assert 'exploratory' in payload['config']['inferential_scope']
    assert payload['sweeps']['sweep_shots']['128']['pairing']['pair_ids'] == [0, 1]


def test_zne_orders_reuse_the_same_noise_levels(monkeypatch) -> None:
    calls = []

    def fake_histogram(lam, shots, seed, iteration):
        calls.append((lam, iteration))
        histogram = np.zeros(256)
        histogram[64] = 1.0
        return histogram

    monkeypatch.setattr(run_zne_comparison, '_run_at_lambda', fake_histogram)
    outcomes = run_zne_comparison.run_zne_strategies(
        shots=32, max_iter=2, seed=7,
        strategies={'ZNE-2': (1, 2), 'ZNE-3': (1, 2, 3)},
    )

    assert calls == [(1.0, 1), (2.0, 1), (3.0, 1)]
    assert outcomes['ZNE-2'] == {
        'iterations': 1, 'success': True, 'shots_used': 64,
    }
    assert outcomes['ZNE-3'] == {
        'iterations': 1, 'success': True, 'shots_used': 96,
    }


def test_zne_extrapolation_uses_the_actual_lambda_grid() -> None:
    # f(lambda)=0.2+0.1*lambda: l'interpolazione lineare su (1,3)
    # deve recuperare f(0)=0.2, non usare implicitamente i coefficienti (2,-1).
    first = np.array([0.3, 0.7])
    third = np.array([0.5, 0.5])
    extrapolated = run_zne_comparison._extrapolate([first, third], (1, 3))
    assert extrapolated == pytest.approx([0.2, 0.8])


@pytest.mark.parametrize('lambdas', [(1, 1), (0, 1), (1, float('nan'))])
def test_zne_rejects_invalid_lambda_grids(lambdas) -> None:
    with pytest.raises(ValueError, match='finiti, positivi e distinti'):
        run_zne_comparison.run_zne_strategies(
            shots=8, max_iter=1, seed=0, strategies={'bad': lambdas}
        )
