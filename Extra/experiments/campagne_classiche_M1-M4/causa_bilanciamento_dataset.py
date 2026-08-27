"""Stub storico del diagnostico pre-v2 sul bilanciamento del dataset.

La premessa basata sul confronto di gate count fra circuiti/transpiler diversi è obsoleta.
Il training v2 registra già regola di etichettatura, bilanciamento, campionamento del rumore,
seed e manifest del circuito in ``training_manifest.json`` e negli audit delle classi uniche.
Questo file resta soltanto per impedire che vecchi comandi rilancino una campagna fuorviante.
"""

from __future__ import annotations

import argparse
import sys


DISABLED_NOTICE = (
    "DIAGNOSTICO STORICO DISABILITATO: la spiegazione basata su gate count pre-v2 non è "
    "confrontabile con il circuito corrente. Eseguire train_classifier.py e usare "
    "training_manifest.json (campo outcomes); per una classe unica consultare anche "
    "label_audit_<UC>.json."
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    parse_args(argv)
    print(DISABLED_NOTICE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
