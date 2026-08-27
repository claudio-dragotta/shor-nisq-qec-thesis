"""Regression indipendente per la copia Beauregard usata dalle campagne della tesi.

Non avvia alcuna campagna e non scrive output: simula soltanto la truth table ideale del
moltiplicatore locale per N=21 e N=35, inclusa la pulizia di registro ausiliario e ancilla.
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


_MODULE_PATH = Path(__file__).with_name("beauregard.py")
_SPEC = importlib.util.spec_from_file_location("campaign_beauregard", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_BEAUREGARD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_BEAUREGARD)


def test_campaign_and_demo_use_the_same_validated_source() -> None:
    """Prevent the vendored copies from silently diverging again."""
    demo_copy = _MODULE_PATH.parents[2] / "shor-demo" / "beauregard.py"
    assert demo_copy.read_bytes() == _MODULE_PATH.read_bytes()


def test_campaign_copy_exposes_the_revision_contract() -> None:
    circuit = _BEAUREGARD.beauregard_c_amod(2, 21, 1)
    assert (
        _BEAUREGARD.BEAUREGARD_REVISION
        == "beauregard-c-amod-v2-endian-clean-ancilla"
    )
    assert circuit.metadata["beauregard_revision"] == _BEAUREGARD.BEAUREGARD_REVISION


def _clean_basis_index(control: int, value: int, width: int) -> int:
    index = int(control)
    for position in range(width):
        if (value >> (width - 1 - position)) & 1:
            index |= 1 << (1 + position)
    return index


@pytest.mark.parametrize(("N", "a"), [(21, 2), (35, 6)])
def test_campaign_copy_full_controlled_truth_table(N: int, a: int) -> None:
    width = math.ceil(math.log2(N + 1))
    gate = _BEAUREGARD.beauregard_c_amod(a, N, 1)
    circuits = []
    expected = []

    for control in (0, 1):
        for value in range(N):
            circuit = QuantumCircuit(gate.num_qubits)
            if control:
                circuit.x(0)
            for position in range(width):
                if (value >> (width - 1 - position)) & 1:
                    circuit.x(1 + position)
            circuit.compose(gate, range(gate.num_qubits), inplace=True)
            circuit.save_probabilities_dict(range(gate.num_qubits), label="truth")
            circuits.append(circuit)
            output = a * value % N if control else value
            expected.append(_clean_basis_index(control, output, width))

    simulator = AerSimulator(method="matrix_product_state", max_parallel_experiments=0)
    result = simulator.run(circuits).result()
    assert result.success
    for experiment, target in enumerate(expected):
        probabilities = result.data(experiment)["truth"]
        assert float(probabilities.get(target, 0.0)) == pytest.approx(1.0, abs=2e-9)
        assert sum(
            float(probability)
            for index, probability in probabilities.items()
            if int(index) != target
        ) < 2e-9
