"""Perche' la regola di etichettatura TOP-16 non puo' produrre una classe negativa.

La ricerca della soglia di rumore oltre la quale compaiono campioni negativi non trova
nessuna soglia: la frazione di negativi satura allo 0.5% e non cresce piu', nemmeno
portando eps_2q a trenta volte il valore dei dispositivi attuali, dove la frazione
coerente efficace e' scesa allo 0.8%.

La causa non e' il rumore ma la regola di etichettatura. `extract_factors` applica le
frazioni continue con limit_denominator(N), che mappa sul periodo r non i soli picchi
esatti ma un'intera banda di fasi attorno a ciascuno. Questo script conta quanti dei
2^n_count esiti possibili conducano ai fattori, e ne ricava il tetto combinatorio alla
frazione di negativi: la probabilita' che, pescando i TOP_K valori piu' frequenti da un
istogramma privo di segnale (dunque uniforme), nessuno di essi risulti utile.
"""
import warnings
from math import comb

warnings.filterwarnings('ignore')

from shor_core import extract_factors

CASI = [
    ('UC1/UC2', 15, 7, 8),
]

for nome, N, a, n_count in CASI:
    n_celle = 2 ** n_count
    utili = [k for k in range(n_celle) if extract_factors(k, n_count, N, a)[0] is not None]
    n_utili = len(utili)
    print(f'=== {nome}: N={N}, a={a}, n_count={n_count}')
    print(f'    esiti che conducono ai fattori: {n_utili}/{n_celle} '
          f'({100 * n_utili / n_celle:.1f}%)')
    print(f'    {utili}\n')

    print(f'    tetto alla frazione di negativi su istogramma uniforme:')
    for top_k in (1, 2, 4, 16):
        if top_k <= n_celle - n_utili:
            p = comb(n_celle - n_utili, top_k) / comb(n_celle, top_k)
        else:
            p = 0.0
        marca = '   <-- regola documentata' if top_k == 16 else ''
        print(f'      TOP-{top_k:<2} : {100 * p:6.2f}% di negativi al massimo{marca}')

    print()
    print('    Nota: il tetto vale per un istogramma privo di segnale. Con segnale')
    print('    presente la frazione e\' ancora minore. La regola TOP-16 etichetta quindi')
    print(f'    positivo il {100 * (1 - comb(n_celle - n_utili, 16) / comb(n_celle, 16)):.1f}% '
          f'degli istogrammi per puro effetto combinatorio.')
    print()
    print('    Per contrasto, con TOP-1 il solo candidato valutato e\' la moda, che')
    print('    cade sempre su uno dei quattro picchi QPE {0, 64, 128, 192}: di questi')
    print('    solo y=0 fallisce, da cui una frazione negativa attesa di circa un')
    print('    quarto — ed e\' il 25.8% osservato nel dataset originale.')
