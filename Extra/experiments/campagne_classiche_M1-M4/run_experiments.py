"""Entry point storico, disabilitato dopo l'erratum del 19 agosto 2026.

La versione originale mescolava circuiti, modelli ML e statistiche appartenenti a
contratti sperimentali differenti. In particolare poteva caricare i classificatori
pre-correzione e attribuire a N=21 un costo compilato non confrontabile con la base
``rz/sx/x/cx``. Il file resta come segnalibro per i link storici, ma non esegue piu'
simulazioni.

Pipeline supportata:

1. ``train_classifier.py``;
2. ``rerun_baseline_corretto.py``;
3. ``run_parameter_analysis.py``;
4. ``run_zne_comparison.py``;
5. ``generate_figures.py`` e ``extract_latex.py``.

Gli artefatti accettabili devono avere ``schema_version = 2.0`` e un manifest
compatibile con il circuito N=15 corretto. L'aritmetica Beauregard N=21/35 e'
validata con test separati; non e' inclusa nella campagna rumorosa per il costo
del circuito completo (N=21, n_count=8: 21.036 CX, profondita' 23.081,
nella base contrattuale dopo ottimizzazione globale).
"""


def main() -> None:
    raise SystemExit(
        "run_experiments.py e' un entry point legacy disabilitato. "
        "Usare la pipeline schema-v2 descritta nel README della campagna."
    )


if __name__ == '__main__':
    main()
