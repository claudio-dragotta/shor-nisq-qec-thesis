"""Entry point statistico storico, disabilitato.

Le repliche della campagna condividono il seed per strategia e costituiscono dati
appaiati. Il precedente Mann--Whitney per campioni indipendenti e la codifica dei
fallimenti a ``MAX_ITER`` non fanno quindi parte del contratto v2.

``rerun_baseline_corretto.py`` calcola ora il Wilcoxon signed-rank unilaterale
con ``zero_method='pratt'`` e sentinel ``MAX_ITER + 1``; ``extract_latex.py``
legge direttamente quei risultati senza rilanciare Aer.
"""


def main() -> None:
    raise SystemExit(
        "mwu_analysis.py e' legacy. Usare rerun_baseline_corretto.py e "
        "extract_latex.py sugli artefatti schema-v2."
    )


if __name__ == '__main__':
    main()
