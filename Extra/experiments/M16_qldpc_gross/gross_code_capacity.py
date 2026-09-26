"""M16 — verifica esplorativa del Gross code [[144,12,12]] nel modello code-capacity.

Il sommario e la tesi citano i codici qLDPC, e in particolare il Gross code di IBM, come
riferimento per architetture con overhead ridotto. Questo script ne fa una prima verifica
numerica, nel modello piu' semplice possibile, con lo stesso decoder BP+OSD gia' usato in
M10/E7 sul surface code.

Modello (code-capacity):
  - errori X indipendenti con probabilita' q su ogni qubit di dato;
  - sindromi perfette, un solo ciclo, nessun errore su porte, preparazione o misura.
Entrambi i codici sono CSS e simmetrici fra X e Z, quindi il canale X basta a
caratterizzare ciascun settore. Il modello NON e' confrontabile con M7, che e' a livello
di circuito: e' un confronto fra codici, non fra architetture.

Codici:
  - Gross code, codice bivariate bicycle con l=12, m=6, A = x^3 + y + y^2,
    B = y^3 + x + x^2 (Bravyi et al., Nature 627, 2024): 144 qubit di dato, 12 logici.
  - Surface code ruotato di distanza d: d^2 qubit di dato, 1 logico.

Decoder: BP+OSD (libreria ldpc) su entrambi i codici; MWPM (PyMatching) sul surface code
come riferimento.

Fallimento logico: il residuo r = errore + correzione soddisfa sempre le sindromi; e' un
errore logico se non appartiene allo spazio delle righe di Hx, cioe' se ha prodotto
scalare non nullo con almeno un vettore del nucleo di Hx. Per il Gross code si conta il
fallimento del blocco (almeno uno dei 12 qubit logici errato).

Uso (ambiente canonico):
    PY=/home/claudio/quantum-env/bin/python
    $PY gross_code_capacity.py --seed 42 --output-dir artifacts/v2_20260926
    $PY gross_code_capacity.py --quick          # prova rapida, senza salvare nulla
"""
import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version

import numpy as np
import pymatching
from ldpc import BpOsdDecoder

SCHEMA_VERSION = "2.0"
Q_LIST = [0.005, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10]
DISTANCES = [3, 5, 7, 9, 11, 13]
N_LOGICI_BLOCCO = 12     # il confronto e' a parita' di qubit logici del Gross code


# --- algebra lineare su GF(2) ---------------------------------------------------------
def gf2_rref(M):
    """Forma ridotta a scalini su GF(2). Restituisce le righe non nulle e le colonne pivot."""
    A = (np.asarray(M, dtype=np.uint8) % 2).copy()
    rows, cols = A.shape
    piv, r = [], 0
    for c in range(cols):
        if r == rows:
            break
        nz = np.nonzero(A[r:, c])[0]
        if nz.size == 0:
            continue
        p = r + nz[0]
        if p != r:
            A[[r, p]] = A[[p, r]]
        mask = A[:, c].astype(bool)
        mask[r] = False
        A[mask] ^= A[r]
        piv.append(c)
        r += 1
    return A[:r], piv


def gf2_rank(M):
    return len(gf2_rref(M)[1])


def gf2_nullspace(M):
    """Base del nucleo {x : M x = 0} su GF(2), una riga per vettore."""
    R, piv = gf2_rref(M)
    n = M.shape[1]
    pivset = set(piv)
    base = []
    for f in (c for c in range(n) if c not in pivset):
        v = np.zeros(n, dtype=np.uint8)
        v[f] = 1
        for i, pc in enumerate(piv):
            v[pc] = R[i, f]
        base.append(v)
    return np.array(base, dtype=np.uint8).reshape(-1, n)


# --- costruzione dei codici -------------------------------------------------------------
def _shift(k):
    return np.roll(np.eye(k, dtype=np.uint8), 1, axis=1)


def bivariate_bicycle(l, m, a_terms, b_terms):
    """Codice bivariate bicycle. I termini sono coppie (asse, potenza) con asse in {x, y}."""
    x = np.kron(_shift(l), np.eye(m, dtype=np.uint8))
    y = np.kron(np.eye(l, dtype=np.uint8), _shift(m))
    base = {'x': x, 'y': y}

    def poly(terms):
        P = np.zeros((l * m, l * m), dtype=np.uint8)
        for asse, potenza in terms:
            P ^= np.linalg.matrix_power(base[asse].astype(np.int64), potenza).astype(np.uint8) % 2
        return P

    A, B = poly(a_terms), poly(b_terms)
    Hx = np.hstack([A, B]) % 2
    Hz = np.hstack([B.T, A.T]) % 2
    return Hx.astype(np.uint8), Hz.astype(np.uint8)


def gross_code():
    return bivariate_bicycle(12, 6, [('x', 3), ('y', 1), ('y', 2)],
                             [('y', 3), ('x', 1), ('x', 2)])


def rotated_surface(d):
    """Surface code ruotato di distanza d: qubit di dato sulla griglia d x d.

    Ogni faccia ha l'angolo in alto a sinistra in (r, c), con r, c in [-1, d-1]. Le facce
    interne sono di peso 4 e alternano Z e X a scacchiera; sul bordo si tengono solo le
    facce di peso 2 del tipo giusto: Z sui bordi superiore e inferiore, X su quelli
    laterali. Le sindromi Z rilevano gli errori X.
    """
    q = lambda r, c: r * d + c
    Hx, Hz = [], []
    for r in range(-1, d):
        for c in range(-1, d):
            angoli = [(r + a, c + b) for a in (0, 1) for b in (0, 1)
                      if 0 <= r + a < d and 0 <= c + b < d]
            tipo_z = (r + c) % 2 == 0
            if len(angoli) == 4:
                pass
            elif len(angoli) == 2:
                bordo_orizzontale = r in (-1, d - 1)
                if tipo_z != bordo_orizzontale:
                    continue
            else:
                continue
            riga = np.zeros(d * d, dtype=np.uint8)
            for rr, cc in angoli:
                riga[q(rr, cc)] = 1
            (Hz if tipo_z else Hx).append(riga)
    return np.array(Hx, dtype=np.uint8), np.array(Hz, dtype=np.uint8)


def verifica_css(Hx, Hz, k_atteso, nome):
    """Controlli strutturali: stabilizzatori che commutano e numero di qubit logici."""
    n = Hx.shape[1]
    commutano = not ((Hx.astype(np.int64) @ Hz.T.astype(np.int64)) % 2).any()
    k = n - gf2_rank(Hx) - gf2_rank(Hz)
    if not commutano or k != k_atteso:
        raise RuntimeError(f"{nome}: verifica CSS fallita (commutano={commutano}, k={k})")
    return {
        'n': int(n), 'k': int(k), 'commutano': bool(commutano),
        'righe_Hx': int(Hx.shape[0]), 'righe_Hz': int(Hz.shape[0]),
        'rank_Hx': int(gf2_rank(Hx)), 'rank_Hz': int(gf2_rank(Hz)),
        'peso_righe_Hz': sorted({int(w) for w in Hz.sum(axis=1)}),
        'peso_colonne_Hz': sorted({int(w) for w in Hz.sum(axis=0)}),
        'sha256_Hx': hashlib.sha256(np.ascontiguousarray(Hx).tobytes()).hexdigest(),
        'sha256_Hz': hashlib.sha256(np.ascontiguousarray(Hz).tobytes()).hexdigest(),
    }


# --- campionamento e decodifica -----------------------------------------------------------
def decodifica_blocco(task):
    """Un blocco di shot: campiona errori X, decodifica, conta i fallimenti logici."""
    Hz, K, q, decoder, shots, seed_words, bp = task
    rng = np.random.default_rng(np.random.SeedSequence(seed_words))
    n = Hz.shape[1]
    err = (rng.random((shots, n)) < q).astype(np.uint8)
    Hz32 = Hz.astype(np.int32)
    synd = ((err.astype(np.int32) @ Hz32.T) % 2).astype(np.uint8)

    if decoder == 'mwpm':
        w = math.log((1 - q) / q)
        m = pymatching.Matching.from_check_matrix(Hz, weights=np.full(n, w))
        corr = m.decode_batch(synd).astype(np.uint8)
    else:
        extra = {}
        if bp.get('ms_scaling_factor') is not None:
            extra['ms_scaling_factor'] = bp['ms_scaling_factor']
        dec = BpOsdDecoder(Hz, error_rate=float(q), max_iter=bp['max_iter'],
                           bp_method=bp['bp_method'], osd_method=bp['osd_method'],
                           osd_order=bp['osd_order'], **extra)
        corr = np.array([dec.decode(s) for s in synd], dtype=np.uint8)

    res = (err ^ corr).astype(np.int32)
    sindromi_violate = int(((res @ Hz32.T) % 2).any(axis=1).sum())
    fallimenti = ((res @ K.astype(np.int32).T) % 2).any(axis=1)
    return int(fallimenti.sum()), sindromi_violate


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (float('nan'), float('nan'))
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    semi = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centro - semi), min(1.0, centro + semi))


def esegui_punto(pool, cfg, q, args, idx_cfg, idx_q):
    Hz, K = cfg['Hz'], cfg['K']
    bp = {'max_iter': args.bp_max_iter, 'bp_method': args.bp_method,
          'osd_method': args.osd_method, 'osd_order': args.osd_order,
          'ms_scaling_factor': args.ms_scaling_factor}
    shots = fall = viol = 0
    blocco = 0
    t0 = time.time()
    while shots < args.shots_max and fall < args.min_failures:
        tasks = []
        for _ in range(args.workers):
            s = min(args.chunk, args.shots_max - shots - sum(t[4] for t in tasks))
            if s <= 0:
                break
            tasks.append((Hz, K, q, cfg['decoder'], s,
                          [args.seed, idx_cfg, idx_q, blocco], bp))
            blocco += 1
        for f, v in pool.map(decodifica_blocco, tasks):
            fall += f
            viol += v
        shots += sum(t[4] for t in tasks)
    lo, hi = wilson(fall, shots)
    return {
        'q': q, 'shots': shots, 'fallimenti': fall,
        'p_fallimento': fall / shots if shots else float('nan'),
        'ic95_wilson': [lo, hi],
        'sindromi_violate': viol, 'secondi': round(time.time() - t0, 2),
    }


def pendenza_loglog(punti, min_fail=20, p_max=0.3):
    """Pendenza di ln p_L contro ln q sui punti con abbastanza fallimenti."""
    sel = [(p['q'], p['p_fallimento']) for p in punti
           if p['fallimenti'] >= min_fail and p['p_fallimento'] < p_max]
    if len(sel) < 2:
        return None
    x = np.log([s[0] for s in sel])
    y = np.log([s[1] for s in sel])
    slope, intercept = np.polyfit(x, y, 1)
    return {'pendenza': float(slope), 'intercetta': float(intercept),
            'q_usati': [s[0] for s in sel]}


# --- manifest -----------------------------------------------------------------------------
def manifest(args, script=None):
    """Metadati della corsa. `script` e' il file che lancia la corsa; se omesso, questo
    modulo. Lo SHA-256 di questo modulo e' registrato comunque come dipendenza."""
    def pv(nome):
        try:
            return version(nome)
        except PackageNotFoundError:
            return 'not-installed'

    qui = os.path.abspath(script or __file__)
    modulo = os.path.abspath(__file__)
    try:
        commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=os.path.dirname(qui),
                                capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        commit = ''
    return {
        'script': os.path.basename(qui),
        'script_sha256': hashlib.sha256(open(qui, 'rb').read()).hexdigest(),
        'modulo_base_sha256': hashlib.sha256(open(modulo, 'rb').read()).hexdigest(),
        'git_commit': commit or 'non-disponibile',
        'argv': sys.argv,
        # alcune corse (es. l'enumerazione esaustiva) sono deterministiche e non hanno seme
        'seed': getattr(args, 'seed', None),
        'python': platform.python_version(),
        'interprete': sys.executable,
        'piattaforma': platform.platform(),
        'cpu': os.cpu_count(),
        'packages': {k: pv(k) for k in ('numpy', 'ldpc', 'PyMatching', 'stim', 'scipy')},
        'timestamp': datetime.now().isoformat(timespec='seconds'),
    }


# --- main ---------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="M16 — Gross code in code-capacity")
    ap.add_argument('--q-list', type=float, nargs='+', default=Q_LIST)
    ap.add_argument('--distances', type=int, nargs='+', default=DISTANCES)
    ap.add_argument('--shots-max', type=int, default=200_000)
    ap.add_argument('--min-failures', type=int, default=1000,
                    help="un punto si ferma appena raggiunge questi fallimenti")
    ap.add_argument('--chunk', type=int, default=2000)
    ap.add_argument('--workers', type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--bp-max-iter', type=int, default=100)
    ap.add_argument('--bp-method', default='product_sum')
    ap.add_argument('--osd-method', default='osd_cs')
    ap.add_argument('--osd-order', type=int, default=10)
    ap.add_argument('--ms-scaling-factor', type=float, default=None,
                    help="fattore di scala del min-sum (se omesso, default di ldpc)")
    ap.add_argument('--decoder-surface', choices=['entrambi', 'mwpm', 'bposd'],
                    default='entrambi')
    ap.add_argument('--senza-gross', action='store_true',
                    help="simula solo il surface code (estensione della statistica)")
    ap.add_argument('--solo-gross', action='store_true',
                    help="simula solo il Gross code (prove di sensibilita' del decoder)")
    ap.add_argument('--etichetta', default='',
                    help="suffisso del file di output, per distinguere le corse")
    ap.add_argument('--output-dir', default=None)
    ap.add_argument('--quick', action='store_true',
                    help="prova rapida: pochi shot, niente file salvato")
    args = ap.parse_args()
    if args.quick:
        args.q_list, args.distances = [0.02, 0.06], [3, 5]
        args.shots_max, args.min_failures, args.chunk = 4000, 10**9, 500
    elif not args.output_dir:
        ap.error("--output-dir e' obbligatorio fuori da --quick")
    if args.solo_gross:
        args.distances = []

    # codici e controlli strutturali
    Hx_g, Hz_g = gross_code()
    codici = {'gross': {'Hx': Hx_g, 'Hz': Hz_g,
                        'verifica': verifica_css(Hx_g, Hz_g, 12, 'Gross code')}}
    for d in args.distances:
        Hx_s, Hz_s = rotated_surface(d)
        codici[f'surface_d{d}'] = {'Hx': Hx_s, 'Hz': Hz_s,
                                   'verifica': verifica_css(Hx_s, Hz_s, 1, f'surface d={d}')}
    for c in codici.values():
        c['K'] = gf2_nullspace(c['Hx'])

    configurazioni = [] if args.senza_gross else [
        {'nome': 'gross_bposd', 'codice': 'gross', 'decoder': 'bposd'}]
    for d in args.distances:
        if args.decoder_surface in ('entrambi', 'mwpm'):
            configurazioni.append({'nome': f'surface_d{d}_mwpm', 'codice': f'surface_d{d}',
                                   'decoder': 'mwpm', 'd': d})
        if args.decoder_surface in ('entrambi', 'bposd'):
            configurazioni.append({'nome': f'surface_d{d}_bposd', 'codice': f'surface_d{d}',
                                   'decoder': 'bposd', 'd': d})

    print("=" * 88)
    print("M16 — Gross code [[144,12,12]] e surface code in code-capacity (errori X)")
    print(f"    q = {args.q_list}   shots max {args.shots_max}   "
          f"stop a {args.min_failures} fallimenti   workers {args.workers}")
    g = codici['gross']['verifica']
    print(f"    Gross: n={g['n']} k={g['k']} rank Hx={g['rank_Hx']} rank Hz={g['rank_Hz']} "
          f"pesi righe {g['peso_righe_Hz']}")
    print("=" * 88)

    risultati = []
    t_tot = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for i_cfg, cfg in enumerate(configurazioni):
            codice = codici[cfg['codice']]
            cfg_run = {'Hz': codice['Hz'], 'K': codice['K'], 'decoder': cfg['decoder']}
            punti = []
            for i_q, q in enumerate(args.q_list):
                pt = esegui_punto(pool, cfg_run, q, args, i_cfg, i_q)
                punti.append(pt)
                print(f"  {cfg['nome']:<20} q={q:<6} p_L={pt['p_fallimento']:.3e} "
                      f"({pt['fallimenti']}/{pt['shots']})  {pt['secondi']}s", flush=True)
                if pt['sindromi_violate']:
                    print(f"    ATTENZIONE: {pt['sindromi_violate']} correzioni non "
                          f"rispettano la sindrome", flush=True)
            voce = {k: v for k, v in cfg.items()}
            voce['n_dati'] = int(codice['Hz'].shape[1])
            voce['k'] = int(codice['verifica']['k'])
            voce['punti'] = punti
            voce['fit_loglog'] = pendenza_loglog(punti)
            risultati.append(voce)

    # confronto a parita' di 12 qubit logici: Gross code contro 12 patch indipendenti
    confronto = []
    gross = next((r for r in risultati if r['nome'] == 'gross_bposd'), None)
    for r in risultati:
        if gross is None or r['codice'] == 'gross' or r['decoder'] != 'mwpm':
            continue
        d = r['d']
        righe = []
        for pg, ps in zip(gross['punti'], r['punti']):
            blocco = lambda p: 1 - (1 - p) ** N_LOGICI_BLOCCO
            righe.append({
                'q': ps['q'],
                'gross_p_blocco': pg['p_fallimento'], 'gross_ic95': pg['ic95_wilson'],
                'surface_p_blocco': blocco(ps['p_fallimento']),
                'surface_ic95': [blocco(ps['ic95_wilson'][0]), blocco(ps['ic95_wilson'][1])],
            })
        confronto.append({
            'd': d,
            'qubit_dati_surface': N_LOGICI_BLOCCO * d * d,
            'qubit_totali_surface': N_LOGICI_BLOCCO * (2 * d * d - 1),
            'qubit_dati_gross': 144, 'qubit_totali_gross': 288,
            'righe': righe,
        })

    if gross is not None:
        print("\nConfronto a 12 qubit logici: P(almeno un logico errato)")
        print(f"  {'q':<7}{'Gross (144/288)':>18}" +
              "".join(f"{'d=' + str(c['d']) + ' (' + str(c['qubit_dati_surface']) + ')':>16}"
                      for c in confronto))
        for i, q in enumerate(args.q_list):
            riga = f"  {q:<7}{gross['punti'][i]['p_fallimento']:>18.3e}"
            riga += "".join(f"{c['righe'][i]['surface_p_blocco']:>16.3e}" for c in confronto)
            print(riga)
    print(f"\nTempo totale: {time.time() - t_tot:.0f}s")

    if args.quick:
        print("\n--quick: nessun file salvato.")
        return

    out = {
        'schema_version': SCHEMA_VERSION,
        'milestone': 'M16_gross_code_capacity',
        'stato': 'esplorativo',
        'modello_rumore': ("code-capacity: errori X indipendenti con probabilita' q sui "
                           "qubit di dato, sindromi perfette, un ciclo"),
        'limite_interpretativo': ("confronto fra codici nello stesso modello code-capacity; "
                                  "non confrontabile con M7 (livello di circuito) ne' con i "
                                  "risultati IBM a livello di circuito"),
        'experiment_manifest': manifest(args),
        'parametri': {
            'etichetta': args.etichetta, 'solo_gross': args.solo_gross,
            'senza_gross': args.senza_gross, 'decoder_surface': args.decoder_surface,
            'ms_scaling_factor': args.ms_scaling_factor,
            'q_list': args.q_list, 'distances': args.distances,
            'shots_max': args.shots_max, 'min_failures': args.min_failures,
            'chunk': args.chunk, 'workers': args.workers,
            'bposd': {'max_iter': args.bp_max_iter, 'bp_method': args.bp_method,
                      'osd_method': args.osd_method, 'osd_order': args.osd_order},
            'mwpm': 'PyMatching, pesi uniformi ln((1-q)/q)',
            'gross_code': {'l': 12, 'm': 6, 'A': 'x^3 + y + y^2', 'B': 'y^3 + x + x^2'},
        },
        'verifiche_codici': {k: v['verifica'] for k, v in codici.items()},
        'risultati': risultati,
        'confronto_12_logici': confronto,
    }
    os.makedirs(args.output_dir, exist_ok=True)
    suffisso = f"_{args.etichetta}" if args.etichetta else ""
    nome = f"results_M16_gross_code_capacity{suffisso}_{datetime.now():%Y%m%d_%H%M%S}.json"
    path = os.path.join(args.output_dir, nome)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print(f"Risultati salvati in: {path}")


if __name__ == '__main__':
    main()
