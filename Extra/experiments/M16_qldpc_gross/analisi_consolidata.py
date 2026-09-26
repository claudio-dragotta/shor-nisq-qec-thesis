"""M16 — confronto consolidato Gross code / surface code a parita' di 12 qubit logici.

Combina corse diverse passate ESPLICITAMENTE (nessuna scelta implicita del file piu'
recente). Per ogni q e ogni configurazione prende, fra i file indicati, il punto con piu'
fallimenti: e' quello con l'intervallo di confidenza piu' stretto.

Uso:
    $PY analisi_consolidata.py \
        --gross-json A.json B.json --gross-config gross_bposd \
        --surface-json C.json D.json \
        --output-dir artifacts/v2_20260926
"""
import argparse
import hashlib
import json
import math
import os
from datetime import datetime

N_LOGICI = 12


def carica(paths):
    return [(p, json.load(open(p, encoding='utf-8'))) for p in paths]


def migliori_punti(sorgenti, filtro):
    """{q: (punto, file)} col punto che ha piu' fallimenti (poi piu' shot) fra le
    configurazioni filtrate."""
    out = {}
    for path, dati in sorgenti:
        for r in dati['risultati']:
            if not filtro(r):
                continue
            for p in r['punti']:
                q = p['q']
                # A parita' di fallimenti (anche zero) vince il punto con piu' shot.
                chiave = (p['fallimenti'], p['shots'])
                if q not in out or chiave > (out[q][0]['fallimenti'], out[q][0]['shots']):
                    out[q] = (p, os.path.basename(path))
    return out


def blocco(p):
    return 1 - (1 - p) ** N_LOGICI


def limite_superiore(p):
    """0 fallimenti su N: limite superiore al 95% (regola del tre)."""
    return 3.0 / p['shots'] if p['fallimenti'] == 0 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gross-json', nargs='+', required=True)
    ap.add_argument('--surface-json', nargs='+', required=True)
    ap.add_argument('--decoder-gross', default='minimum_sum',
                    help="bp_method richiesto nei file del Gross code")
    ap.add_argument('--ms-scaling-factor', type=float, default=0.625)
    ap.add_argument('--variante-gross', default=None,
                    help="per i file del test 4 (famiglia_bb): variante di decoder "
                         "richiesta, per nome (es. serial)")
    ap.add_argument('--etichetta', default='', help="suffisso del file di output")
    ap.add_argument('--output-dir', required=True)
    args = ap.parse_args()

    gross_src = carica(args.gross_json)
    decoder_gross = None
    for path, d in gross_src:
        if d.get('milestone') == 'M16_test4_famiglia_bb':
            nome_var = next(iter(d['parametri']['decoder']))
            if nome_var != args.variante_gross:
                raise SystemExit(f"{path}: variante {nome_var}, attesa {args.variante_gross}")
            decoder_gross = {nome_var: d['parametri']['decoder'][nome_var]}
            continue
        bp = d['parametri']['bposd']
        msf = d['parametri'].get('ms_scaling_factor')
        if bp['bp_method'] != args.decoder_gross or msf != args.ms_scaling_factor:
            raise SystemExit(f"{path}: decoder {bp['bp_method']} / scala {msf}, "
                             f"atteso {args.decoder_gross} / {args.ms_scaling_factor}")
    surf_src = carica(args.surface_json)

    # corse di gross_code_capacity ('nome') o del test 4 ('codice')
    gross = migliori_punti(gross_src, lambda r: r.get('nome') == 'gross_bposd' or
                           r.get('codice') == 'gross_144_12_12')
    distanze = sorted({r['d'] for _, d in surf_src for r in d['risultati']
                       if r.get('decoder') == 'mwpm'})
    surface = {d: migliori_punti(surf_src, lambda r, d=d: r.get('d') == d and
                                 r['decoder'] == 'mwpm') for d in distanze}

    righe = []
    for q in sorted(gross):
        pg, fg = gross[q]
        riga = {'q': q, 'gross': {'p_blocco': pg['p_fallimento'],
                                  'ic95': pg['ic95_wilson'],
                                  'fallimenti': pg['fallimenti'], 'shots': pg['shots'],
                                  'file': fg},
                'surface_12_patch': {}}
        migliori_di_gross, peggiori_di_gross = [], []
        for d in distanze:
            if q not in surface[d]:
                continue
            ps, fs = surface[d][q]
            ls = limite_superiore(ps)
            val = blocco(ls) if ls is not None else blocco(ps['p_fallimento'])
            riga['surface_12_patch'][str(d)] = {
                'p_blocco': val, 'solo_limite_superiore': ls is not None,
                'ic95': [blocco(ps['ic95_wilson'][0]), blocco(ps['ic95_wilson'][1])],
                'fallimenti': ps['fallimenti'], 'shots': ps['shots'], 'file': fs,
                'qubit_dati': N_LOGICI * d * d,
            }
            # Distanze "equivalenti": confronto fra intervalli, non fra stime puntuali.
            lo_s, hi_s = riga['surface_12_patch'][str(d)]['ic95']
            if ls is not None:
                lo_s, hi_s = 0.0, val
            lo_g, hi_g = pg['ic95_wilson']
            if hi_s < lo_g:
                migliori_di_gross.append(d)
            elif lo_s > hi_g:
                peggiori_di_gross.append(d)
        riga['surface_peggiori_del_gross'] = peggiori_di_gross
        riga['surface_migliori_del_gross'] = migliori_di_gross
        righe.append(riga)

    print(f"{'q':<7}{'Gross':>12}  " + "".join(f"{'12xd=' + str(d):>12}" for d in distanze)
          + "   peggiori / migliori del Gross")
    for r in righe:
        s = f"{r['q']:<7}{r['gross']['p_blocco']:>12.2e}  "
        for d in distanze:
            c = r['surface_12_patch'].get(str(d))
            if c is None:
                cella = '-'
            else:
                prefisso = '<' if c['solo_limite_superiore'] else ''
                cella = f"{prefisso}{c['p_blocco']:.2e}"
            s += f"{cella:>12}"
        s += f"   {r['surface_peggiori_del_gross']} / {r['surface_migliori_del_gross']}"
        print(s)

    def sha(p):
        return hashlib.sha256(open(p, 'rb').read()).hexdigest()

    out = {
        'schema_version': '2.0',
        'milestone': 'M16_analisi_consolidata',
        'stato': 'esplorativo',
        'input': {'gross': {os.path.basename(p): sha(p) for p in args.gross_json},
                  'surface': {os.path.basename(p): sha(p) for p in args.surface_json}},
        'decoder_gross': decoder_gross or {'bp_method': args.decoder_gross,
                                           'ms_scaling_factor': args.ms_scaling_factor},
        'decoder_surface': 'MWPM (PyMatching)',
        'regola': ("per ogni q e configurazione si usa il punto con piu' fallimenti fra i "
                   "file indicati; 0 fallimenti -> limite superiore 3/N; una distanza e' "
                   "'migliore' o 'peggiore' del Gross solo se gli IC 95% non si sovrappongono"),
        'script_sha256': sha(os.path.abspath(__file__)),
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'righe': righe,
    }
    os.makedirs(args.output_dir, exist_ok=True)
    path = os.path.join(args.output_dir,
                        f"analysis_M16_consolidata{'_' + args.etichetta if args.etichetta else ''}"
                        f"_{datetime.now():%Y%m%d_%H%M%S}.json")
    json.dump(out, open(path, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print(f"\nSalvato: {path}")


if __name__ == '__main__':
    main()
