"""Guardrail scientifico per il moltiplicatore modulare usato nelle campagne N=15."""

from qiskit import QuantumCircuit
import pytest
from qiskit.quantum_info import Statevector

from shor_core import (
    BASIS_GATES,
    build_noise_model,
    c_amod15,
    compile_shor_circuit,
    experiment_manifest,
    extract_factors,
    rank_measurements,
    shor_circuit,
)


def _reverse_four_bits(value: int) -> int:
    return int(f"{value:04b}"[::-1], 2)


def _output(control: int, value: int, power: int = 1) -> int:
    circuit = QuantumCircuit(5)
    if control:
        circuit.x(0)
    physical = _reverse_four_bits(value)
    for qubit in range(4):
        if (physical >> qubit) & 1:
            circuit.x(qubit + 1)
    circuit.append(c_amod15(7, power), range(5))
    probabilities = Statevector.from_instruction(circuit).probabilities()
    output_index = int(probabilities.argmax())
    assert probabilities[output_index] > 1 - 1e-12
    return _reverse_four_bits(output_index >> 1)


def test_inactive_control_is_identity_on_every_basis_state() -> None:
    assert [_output(0, value) for value in range(16)] == list(range(16))


def test_controlled_truth_table_for_all_valid_modular_values() -> None:
    for power in (1, 2, 4, 8):
        for value in range(1, 15):
            assert _output(1, value, power) == (pow(7, power, 15) * value) % 15


def test_order_four_orbit_is_the_expected_modular_orbit() -> None:
    orbit = [1]
    for _ in range(4):
        orbit.append(_output(1, orbit[-1]))

    assert orbit == [1, 7, 4, 13, 1]


def test_ideal_qpe_has_only_the_four_order_peaks() -> None:
    circuit = shor_circuit(15, 7, 8).remove_final_measurements(inplace=False)
    distribution = Statevector.from_instruction(circuit).probabilities_dict(
        qargs=range(8)
    )
    nonzero = {
        int(bits, 2): float(probability)
        for bits, probability in distribution.items()
        if probability > 1e-12
    }

    assert set(nonzero) == {0, 64, 128, 192}
    assert list(nonzero.values()) == pytest.approx([0.25] * 4, abs=1e-12)
    assert extract_factors(0, 8, 15, 7) == (None, None)
    for outcome in (64, 128, 192):
        assert set(extract_factors(outcome, 8, 15, 7)) == {3, 5}


def test_compilation_and_noise_model_share_the_explicit_physical_basis() -> None:
    circuit = compile_shor_circuit(15, 7, 8)
    assert set(circuit.count_ops()) <= set(BASIS_GATES) | {'measure', 'barrier'}

    model = build_noise_model(1e-3, 1e-2, 100_000, 80_000, p_ro=0.02)
    assert set(model.noise_instructions) == {'sx', 'x', 'cx', 'measure'}
    assert 'rz' not in model.noise_instructions


def test_experiment_manifest_is_deterministic_and_identifies_the_circuit() -> None:
    first = experiment_manifest()
    second = experiment_manifest()
    assert first == second
    # L'hash identifica esattamente l'artefatto compilato ed e' salvato nei
    # risultati. Non viene fissato tra release diverse di Qiskit: una diversa
    # versione del transpiler puo' produrre un circuito equivalente ma differente.
    assert len(first['circuit_sha256']) == 64
    int(first['circuit_sha256'], 16)
    assert first['gate_counts']['cx'] == 224
    assert first['postprocess_revision'] == 'seeded-sha256-tie-break-v1'


def test_measurement_ranking_has_a_seeded_order_independent_tie_break() -> None:
    forward = {'00000000': 10, '01000000': 10, '10000000': 4}
    reverse = dict(reversed(list(forward.items())))

    ranked = rank_measurements(forward, 1234)
    assert ranked == rank_measurements(reverse, 1234)
    assert ranked[-1][0] == '10000000'

    # Il seed puo' cambiare equamente l'esito di un pareggio; non viene imposto
    # un vantaggio sistematico alla bitstring numericamente minore.
    winners = {
        rank_measurements(forward, seed)[0][0]
        for seed in range(20)
    }
    assert winners == {'00000000', '01000000'}
