"""M16 — codici bivariate bicycle della famiglia del Gross code.

Polinomi dalla tabella dei codici di Bravyi et al., "High-threshold and low-overhead
fault-tolerant quantum memory", Nature 627 (2024). Ogni termine e' una coppia
(asse, potenza); ('x', 0) e' l'identita'. n e k attesi sono controllati da verifica_css
prima di ogni uso; la distanza e' quella pubblicata e si controlla con cerca_distanza.py.
"""
from gross_code_capacity import bivariate_bicycle, rotated_surface

CODICI_BB = {
    'bb_72_12_6': {
        'l': 6, 'm': 6, 'n': 72, 'k': 12, 'd_pubblicata': 6,
        'A': [('x', 3), ('y', 1), ('y', 2)], 'B': [('y', 3), ('x', 1), ('x', 2)],
    },
    'bb_90_8_10': {
        'l': 15, 'm': 3, 'n': 90, 'k': 8, 'd_pubblicata': 10,
        'A': [('x', 9), ('y', 1), ('y', 2)], 'B': [('x', 0), ('x', 2), ('x', 7)],
    },
    'bb_108_8_10': {
        'l': 9, 'm': 6, 'n': 108, 'k': 8, 'd_pubblicata': 10,
        'A': [('x', 3), ('y', 1), ('y', 2)], 'B': [('y', 3), ('x', 1), ('x', 2)],
    },
    'gross_144_12_12': {
        'l': 12, 'm': 6, 'n': 144, 'k': 12, 'd_pubblicata': 12,
        'A': [('x', 3), ('y', 1), ('y', 2)], 'B': [('y', 3), ('x', 1), ('x', 2)],
    },
    'bb_288_12_18': {
        'l': 12, 'm': 12, 'n': 288, 'k': 12, 'd_pubblicata': 18,
        'A': [('x', 3), ('y', 2), ('y', 7)], 'B': [('y', 3), ('x', 1), ('x', 2)],
    },
}


def costruisci(nome):
    """(Hx, Hz, k atteso, distanza attesa) per un codice BB o per 'surface_dN'."""
    if nome.startswith('surface_d'):
        d = int(nome[len('surface_d'):])
        Hx, Hz = rotated_surface(d)
        return Hx, Hz, 1, d
    c = CODICI_BB[nome]
    Hx, Hz = bivariate_bicycle(c['l'], c['m'], c['A'], c['B'])
    return Hx, Hz, c['k'], c['d_pubblicata']
