"""Guardrail per la propagazione M10 -> M8.

La propagazione storica interpolava direttamente la curva M8 usando ``pL_mwpm``
e ``pL_hybrid`` di M10. Le grandezze non hanno pero' la stessa unita' statistica:

* M10 misura una probabilita' di fallimento dell'osservabile in un esperimento
  di memoria/decodifica;
* M8 usa la probabilita' fenomenologica di un Pauli non-identita' applicato
  indipendentemente dopo *ogni gate compilato* di Shor.

Senza un modello esplicito che trasformi la prima metrica nella seconda,
l'interpolazione produce numeri precisi ma privi di significato causale. Questo
entry point resta come segnalibro per i riferimenti storici e fallisce in modo
esplicito. Il vecchio ``propagazione_su_shor.json`` e' conservato solo come audit.
"""

import argparse


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description='Propagazione M10->M8 disabilitata: manca un mapping di metrica.'
    )
    parser.parse_args(argv)
    parser.exit(
        2,
        'Operazione non scientificamente identificata: p_L di M10 e il proxy per-gate '
        'di M8 non sono intercambiabili. Definire e validare prima un modello di mapping.\n',
    )


if __name__ == '__main__':
    main()
