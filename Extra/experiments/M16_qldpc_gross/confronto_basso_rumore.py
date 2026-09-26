"""M16 — confronto a basso rumore fra Gross code e surface code dalla decomposizione per peso.

A q = 0,5–1% i fallimenti diretti sono troppo rari (servirebbero 10⁹–10¹⁰ shot). Si usa
invece p_L(q) = Σ_w B(w; n, q) f(w), con f(w) dall'output di analisi_fallimenti.py:
per il Gross i pesi bassi vengono dall'enumerazione esaustiva, per il surface dalla
garanzia di MWPM; i pesi intermedi sono campionati. I limiti inferiore e superiore
propagano gli IC di f(w) e trattano i pesi non campionati come f = 0 / f = 1.

Il blocco Gross (12 logici) si confronta con 12 patch di surface indipendenti,
1 − (1 − p_L)^12. Una distanza e' "migliore" o "peggiore" del Gross solo se gli
intervalli non si sovrappongono.

Uso:
    $PY confronto_basso_rumore.py --input-json <analisi_fallimenti ...json> \
        --output-dir artifacts/v2_20260926
"""
import argparse
import hashlib
import json
import os
from datetime import datetime

from analisi_fallimenti import ricostruisci

N_LOGICI = 12
Q_DEFAULT = [0.002, 0.003, 0.005, 0.0075, 0.01, 0.015, 0.02]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input-json', nargs='+', required=True)
    ap.add_argument('--q-list', type=float, nargs='+', default=Q_DEFAULT)
    ap.add_argument('--decoder-gross', default='serial',
                    help="quale curva del Gross usare se il file ne contiene piu' d'una")
    ap.add_argument('--output-dir', required=True)
    args = ap.parse_args()

    curve = {}
    for p in args.input_json:
        d = json.load(open(p, encoding='utf-8'))
        for r in d['risultati']:
            f_per_w = {x['w']: (x['f'], x['ic95_wilson'][0], x['ic95_wilson'][1])
                       for x in r['per_peso']}
            curve[(r['codice'], r['decoder'])] = (r['n'], f_per_w, os.path.basename(p))

    gross = [k for k in curve if k[0].startswith('gross') and k[1] == args.decoder_gross]
    surf = sorted((k for k in curve if k[0].startswith('surface')),
                  key=lambda k: int(k[0][len('surface_d'):]))
    if len(gross) != 1:
        raise SystemExit(f"attesa una sola curva del Gross code, trovate {gross}")
    g = gross[0]

    def blocco(p):
        return 1 - (1 - p) ** N_LOGICI

    righe = []
    print(f"{'q':<8}{'Gross [basso, alto]':>34}   " +
          "".join(f"{'12x' + k[0][8:]:>30}" for k in surf))
    for q in args.q_list:
        n, fw, _ = curve[g]
        gs, gl, gh = ricostruisci(n, fw, q)
        riga = {'q': q, 'gross': {'p_blocco': gs, 'limiti': [gl, gh]}, 'surface': {},
                'surface_peggiori_del_gross': [], 'surface_migliori_del_gross': []}
        testo = f"{q:<8}{gs:>12.2e} [{gl:.2e}, {gh:.2e}]   "
        for k in surf:
            n_s, fw_s, _ = curve[k]
            ss, sl, sh = (blocco(x) for x in ricostruisci(n_s, fw_s, q))
            dist = int(k[0][len('surface_d'):])
            riga['surface'][str(dist)] = {'p_blocco': ss, 'limiti': [sl, sh]}
            if sh < gl:
                riga['surface_migliori_del_gross'].append(dist)
            elif sl > gh:
                riga['surface_peggiori_del_gross'].append(dist)
            testo += f"{ss:>12.2e} [{sl:.1e}, {sh:.1e}]"
        righe.append(riga)
        print(testo + f"   peggiori {riga['surface_peggiori_del_gross']} / migliori "
              f"{riga['surface_migliori_del_gross']}")

    out = {
        'schema_version': '2.0',
        'milestone': 'M16_confronto_basso_rumore',
        'stato': 'esplorativo',
        'metodo': ("p_L(q) = somma su w di B(w; n, q) f(w); pesi bassi da enumerazione "
                   "esaustiva (Gross) o garanzia MWPM (surface); limiti da IC di f(w)"),
        'decoder_gross': args.decoder_gross,
        'input': {os.path.basename(p): hashlib.sha256(open(p, 'rb').read()).hexdigest()
                  for p in args.input_json},
        'script_sha256': hashlib.sha256(open(os.path.abspath(__file__), 'rb')
                                        .read()).hexdigest(),
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'righe': righe,
    }
    os.makedirs(args.output_dir, exist_ok=True)
    path = os.path.join(args.output_dir,
                        f"analysis_M16_confronto_basso_rumore_{datetime.now():%Y%m%d_%H%M%S}.json")
    json.dump(out, open(path, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print(f"\nSalvato: {path}")


if __name__ == '__main__':
    main()
