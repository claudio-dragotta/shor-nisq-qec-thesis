"""Che cosa ha imparato davvero il classificatore della prima campagna?

`train_classifier.py` documenta la regola di etichettatura come TOP_K = 16: un
istogramma e' positivo se almeno una delle sedici misure piu' frequenti produce i
fattori. Rigenerando oggi il dataset con quella regola si ottengono 2000 campioni
tutti positivi: la classe negativa non esiste.

I classificatori salvati a maggio 2026, invece, contengono un test set con il 25.8%
(UC1) e il 16.8% (UC2) di negativi. Questo script stabilisce quale regola abbia
effettivamente prodotto quelle etichette, ricalcolandole dagli istogrammi salvati
dentro il .joblib e confrontandole con quelle memorizzate.

Esito: le etichette combaciano con la regola TOP-1 (la sola moda), non con TOP-16 —
e tutti i campioni negativi, senza eccezione, sono quelli la cui moda vale y=0.
Il classificatore non ha quindi imparato a riconoscere istogrammi privi di segnale
QPE: ha imparato a riconoscere se l'argmax dell'istogramma cade sull'esito banale.
Da cui, in un colpo solo, sia le metriche eccellenti sia il contributo operativo
nullo — perche' e' esattamente il caso che la ricerca TOP-K risolve per costruzione.
"""
import warnings

warnings.filterwarnings('ignore')

import joblib
import numpy as np

from shor_core import extract_factors

N, A, N_COUNT = 15, 7, 8
PICCHI_QPE = [0, 64, 128, 192]          # j * 2^n_count / r con r = 4


def etichetta(istogramma, top_k):
    """Riproduce la regola di train_classifier.py con un dato TOP_K."""
    idx = np.argsort(-istogramma)[:top_k]
    return int(any(extract_factors(int(k), N_COUNT, N, A)[0] is not None for k in idx))


for uc in ('UC1', 'UC2'):
    d = joblib.load(f'clf_{uc}_campagna_originale.joblib')
    X, y = d['X_test'], d['y_test']
    n_neg = int((1 - y).sum())

    print(f'=== {uc} — modello selezionato: {d["name"]}')
    print(f'    test set {len(y)} campioni, {int(y.sum())} positivi, {n_neg} negativi '
          f'({100 * n_neg / len(y):.1f}%)')

    print('    concordanza fra etichette salvate e regola ricalcolata:')
    for k in (1, 2, 4, 16):
        ric = np.array([etichetta(r, k) for r in X])
        marca = '  <-- regola documentata' if k == 16 else ''
        print(f'      TOP-{k:<2} : {int((ric == y).sum()):3d}/{len(y)} '
              f'({100 * (ric == y).mean():5.1f}%){marca}')

    moda = X.argmax(axis=1)
    print(f'    negativi con moda == 0 : {int((moda[y == 0] == 0).sum())}/{n_neg}')
    print(f'    positivi con moda == 0 : {int((moda[y == 1] == 0).sum())}/{int(y.sum())}')

    # I negativi non sono istogrammi piatti: il segnale QPE c'e' tutto.
    neg = X[y == 0]
    ent = np.mean([-np.sum(r[r > 0] * np.log2(r[r > 0])) for r in neg])
    print(f'    sui negativi: massa media sui quattro picchi QPE '
          f'{neg[:, PICCHI_QPE].sum(axis=1).mean():.3f}, '
          f'entropia media {ent:.2f} bit (uniforme = {N_COUNT} bit)')
    print()
