import json
import random
import sys

import pytest
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import average_gate_fidelity
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke

import analisi_ruoli as AR
import pilota_layout as P
import test_ruoli as R


@pytest.fixture(scope='module')
def backend_calibration():
    backend = FakeSherbrooke()
    return backend, P.leggi_calibrazione(backend)


def test_calibration_has_separate_x_fields_and_stable_hash(backend_calibration):
    _, cal = backend_calibration
    assert set(cal) == {
        'readout', 'sx_err', 'sx_dur', 'x_err', 'x_dur', 'ecr', 'ecr_dur'
    }
    assert cal['x_err'] is not cal['sx_err']
    assert cal['x_dur'] is not cal['sx_dur']
    digest = P.calibration_hash(cal)
    assert len(digest) == 64
    assert digest == P.calibration_hash(cal)


@pytest.mark.parametrize(('n_qubits', 'error'), [(1, 1e-3), (2, 1e-2)])
def test_depolarizing_channel_matches_target_average_infidelity(n_qubits, error):
    channel = P.depolarizing_from_average_error(error, n_qubits)
    measured = 1.0 - float(average_gate_fidelity(channel))
    assert measured == pytest.approx(error, abs=1e-12)


def test_depolarizing_channel_domain():
    assert P.depolarizing_from_average_error(0.0, 1) is None
    with pytest.raises(ValueError):
        P.depolarizing_from_average_error(-1e-3, 1)
    with pytest.raises(ValueError):
        P.depolarizing_from_average_error(0.9, 1)


def test_directed_coupling_and_full_n15_compile_smoke(backend_calibration):
    _, cal = backend_calibration
    adjacency = P.coupling_non_orientata(cal)
    layout = P.campiona_layout(adjacency, 1, P.N_QUBITS, random.Random(42))[0]
    coupling = P.coupling_ridotta(layout, cal)
    assert coupling
    for reduced_a, reduced_b in coupling:
        assert (layout[reduced_a], layout[reduced_b]) in cal['ecr']

    circuit = P.shor_circuit(P.N, P.A, P.N_COUNT)
    compiled = transpile(circuit, basis_gates=P.BASIS, coupling_map=coupling,
                         optimization_level=1, seed_transpiler=42)
    P.assert_ecr_calibrati(compiled, layout, cal)
    assert compiled.count_ops().get('ecr', 0) > 0
    assert all(cal['ecr'][edge] > 0 for edge in P.ecr_fisici(compiled, layout))
    assert 0.0 <= P.punteggio_fedelta(compiled, layout, cal) <= 1.0


def test_ecr_assertion_rejects_reverse_direction(backend_calibration):
    _, cal = backend_calibration
    edge = next(edge for edge in cal['ecr'] if (edge[1], edge[0]) not in cal['ecr'])
    circuit = QuantumCircuit(2)
    circuit.ecr(1, 0)
    with pytest.raises(AssertionError, match='senza calibrazione diretta'):
        P.assert_ecr_calibrati(circuit, [edge[0], edge[1]], cal)


def test_seed_and_shot_schedules_are_reproducible():
    assert P.seed_schedule(42, 4, stream=11) == P.seed_schedule(42, 4, stream=11)
    assert P.seed_schedule(42, 4, stream=11) != P.seed_schedule(42, 4, stream=12)
    sizes = P.split_shots(1027, 8)
    assert sum(sizes) == 1027
    assert max(sizes) - min(sizes) <= 1


def test_measurement_mapping_uses_final_physical_wires(backend_calibration):
    _, cal = backend_calibration
    layout = [0, 1]
    circuit = QuantumCircuit(2, 1)
    circuit.measure(1, 0)
    assert R.qubit_fisici_misurati(circuit, layout) == [1]
    assert R.readout_dei_misurati(circuit, layout, cal) == pytest.approx(cal['readout'][1])


def test_m11b_checkpoint_is_atomic_resumable_and_configuration_bound(tmp_path):
    checkpoint = tmp_path / 'checkpoint.json'
    signature = {'seed': 42, 'shots_per_strategy': 8192}
    rows = [{
        'subgraph_id': 0,
        'sottografo': list(range(12)),
        'strategie': {'transpiler': {'P_success': 0.5}},
    }]
    failures = [{'subgraph_id': 0, 'strategy': 'casuale-1',
                 'error_type': 'ValueError', 'message': 'test'}]

    R._save_checkpoint(checkpoint, signature, rows, failures)
    assert checkpoint.exists()
    assert not checkpoint.with_suffix('.json.tmp').exists()
    loaded_rows, loaded_failures = R._load_checkpoint(
        checkpoint, signature, [list(range(12))]
    )
    assert loaded_rows == rows
    assert loaded_failures == failures

    with pytest.raises(ValueError, match='configurazione diversa'):
        R._load_checkpoint(checkpoint, {'seed': 43}, [list(range(12))])


def _synthetic_rows():
    rows = []
    strategy_offsets = {
        'init-readout-basso': (0.000, 4, -3),
        'init-readout-alto': (0.012, -2, 5),
        'transpiler': (0.006, 1, -1),
        'casuale-1': (0.009, -4, 2),
    }
    for group in range(6):
        strategies = {}
        for index, (name, (ro_delta, ecr_delta, depth_delta)) in enumerate(
                strategy_offsets.items()):
            if group == 2 and name == 'casuale-1':
                continue  # verifica che un fallimento non disallinei i sottografi
            readout = 0.02 + 0.0003 * group + ro_delta
            ecr = 330 + 2 * group + ecr_delta
            depth = 1200 + 3 * group + depth_delta
            success = 0.78 - 3.2 * readout - 0.00015 * ecr - 0.00003 * depth
            strategies[name] = {
                'P_success': success,
                'holdout': {'P_success': success + (index % 2) * 0.0002},
                'readout_misurati': readout,
                'n_ecr': ecr,
                'depth': depth,
            }
        rows.append({'subgraph_id': group, 'sottografo': list(range(12)),
                     'strategie': strategies})
    return rows


def test_observational_analysis_is_aligned_tie_safe_and_strict_json():
    summary = AR.analizza_righe(_synthetic_rows(), seed=7, n_bootstrap=50)
    assert summary['analysis_type'].startswith('observational')
    assert summary['n_subgraphs'] == 6
    assert summary['n_observations'] == 23
    assert summary['controlled_fit']['partial_spearman_readout'] < 0
    assert 'causal' in summary['interpretation'].lower()
    encoded = json.dumps(summary, allow_nan=False)
    assert 'NaN' not in encoded


def test_spearman_is_tie_safe():
    assert P.safe_spearman([1, 1, 2, 2], [4, 4, 1, 1]) == pytest.approx(-1.0)


def test_analysis_cli_requires_explicit_input_and_writes_schema2(tmp_path, monkeypatch):
    source = tmp_path / 'm11b.json'
    output = tmp_path / 'analysis'
    source.write_text(json.dumps({
        'schema_version': '2.0',
        'milestone': 'M11b_ruoli',
        'seed': 42,
        'backend': {'calibration_sha256': 'a' * 64},
        'noise_model': {'revision': AR.EXPECTED_NOISE_REVISION},
        'manifest': {
            'circuit_revision': 'test-circuit',
            'noise_model_revision': 'test-noise',
            'postprocess_revision': 'test-postprocess',
            'circuit_sha256': 'b' * 64,
            'basis_gates': ['rz', 'sx', 'x', 'cx'],
            'optimization_level': 2,
            'seed_transpiler': 42,
        },
        'righe': _synthetic_rows(),
    }), encoding='utf-8')
    monkeypatch.setattr(sys, 'argv', [
        'analisi_ruoli.py', '--input-json', str(source), '--output-dir', str(output),
        '--bootstrap', '10',
    ])
    AR.main()
    files = list(output.glob('analysis_M11b_v2_*.json'))
    assert len(files) == 1
    result = json.loads(files[0].read_text(encoding='utf-8'))
    assert result['schema_version'] == '2.0'
    assert result['source']['calibration_sha256'] == 'a' * 64
    assert result['analysis']['analysis_type'].startswith('observational')
