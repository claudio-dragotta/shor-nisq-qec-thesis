"""Diagnostica del gate count per l'implementazione Beauregard validata.

Il vecchio script conteneva una seconda implementazione completa dell'aritmetica modulare:
la diagnostica poteva quindi continuare a misurare il circuito errato anche dopo una correzione
di ``beauregard.py``. Ora importa esclusivamente la sorgente usata da ``shor_core`` e compila
nella stessa base contrattuale RZ/SX/X/CX.

Esecuzione manuale (non avvia simulazioni rumorose o campagne):
    python test_beauregard_cx.py
"""
from __future__ import annotations

from qiskit import transpile

from beauregard import BEAUREGARD_REVISION, beauregard_c_amod
from shor_core import BASIS_GATES, TRANSPILE_SEED, inverse_qft


def _compiled_metrics(circuit) -> dict:
    compiled = transpile(
        circuit,
        basis_gates=list(BASIS_GATES),
        optimization_level=2,
        seed_transpiler=TRANSPILE_SEED,
    )
    operations = {str(name): int(count) for name, count in compiled.count_ops().items()}
    return {
        "cx": operations.get("cx", 0),
        "depth": int(compiled.depth()),
        "size": int(compiled.size()),
        "operations": operations,
    }


def main() -> None:
    N, a, n_count = 21, 2, 8
    print(f"=== Beauregard validato: N={N}, a={a}, n_count={n_count} ===")
    print(f"revisione: {BEAUREGARD_REVISION}")
    print(f"base di compilazione: {', '.join(BASIS_GATES)}")

    total_cx = 0
    cache: dict[int, dict] = {}
    for count_qubit in range(n_count):
        power = 2 ** count_qubit
        multiplier = pow(a, power, N)
        if multiplier == 1:
            print(
                f"  j={count_qubit}  a^{power:4d} mod {N} = 1"
                "  -> identita', gate omesso"
            )
            continue
        cached = multiplier in cache
        if not cached:
            cache[multiplier] = _compiled_metrics(beauregard_c_amod(a, N, power))
        metrics = cache[multiplier]
        total_cx += metrics["cx"]
        suffix = " [cached]" if cached else ""
        print(
            f"  j={count_qubit}  a^{power:4d} mod {N} = {multiplier:2d}"
            f"  -> CX={metrics['cx']}, depth={metrics['depth']}{suffix}"
        )

    qft_metrics = _compiled_metrics(inverse_qft(n_count))
    grand_total = total_cx + qft_metrics["cx"]
    print(f"CX modular exponentiation: {total_cx}")
    print(f"CX inverse QFT: {qft_metrics['cx']}")
    print(f"CX complessivi: {grand_total}")

    print("P_survival illustrativa in funzione di eps_2q:")
    for epsilon in (0.01, 0.005, 0.002, 0.001, 0.0005, 0.0002):
        survival = (1.0 - epsilon) ** grand_total
        print(f"  eps={epsilon:.4f}  P_surv={survival:.6e}")


if __name__ == "__main__":
    main()
