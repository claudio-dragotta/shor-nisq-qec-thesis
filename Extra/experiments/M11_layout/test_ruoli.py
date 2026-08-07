"""
test_ruoli.py — M11b: conta *quale ruolo* diamo ai qubit, a parita' di sottografo?

PERCHE'. Il pilota (pilota_layout.py) ha variato QUALE gruppo di 12 qubit fisici usare,
lasciando pero' al transpiler la scelta di quale ruolo dare a ciascuno. Ha quindi risposto a
"il punteggio di fedelta' sceglie bene il sottografo?" (si', sbaglia di ~2 p.p. su 43), NON
all'ipotesi di partenza, che era un'altra:

    assegnare i qubit di CONTEGGIO ai qubit fisici con readout migliore aiuta?

La diagnostica del pilota indica che e' li' che bisogna guardare: fra tutte le grandezze
misurate, il readout e' quella che predice meglio il successo (Spearman -0.564, contro +0.032
del numero di porte di routing) --- e gli unici qubit letti sono gli 8 di conteggio, perche'
il registro di lavoro viene scartato senza essere misurato.

DISEGNO. Si FISSA il sottografo e si varia SOLO l'assegnazione dei ruoli al suo interno:

    conteggio-migliore : i virtuali 0..7 (conteggio) sui fisici a readout piu' BASSO
    conteggio-peggiore : i virtuali 0..7 sui fisici a readout piu' ALTO
    transpiler         : scelta libera del transpiler (initial_layout=None)
    casuale            : permutazione casuale (distribuzione di riferimento)

Stesso sottografo, stessi shot, stesso seed: il confronto e' appaiato. Se "conteggio-migliore"
batte sistematicamente "conteggio-peggiore", l'ipotesi regge e ha una leva concreta; se no, la
strada si chiude con una risposta pulita.

Uso: ~/quantum-env/bin/python test_ruoli.py [--sottografi 10] [--shots 8192]
"""
import argparse
import json
import random
import warnings
from datetime import datetime

import numpy as np
from qiskit import transpile
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke

import pilota_layout as P

warnings.filterwarnings('ignore')
N_COUNT = P.N_COUNT          # 8 qubit di conteggio (virtuali 0..7), misurati
N_WORK = 4                   # 4 qubit di lavoro   (virtuali 8..11), scartati


def readout_dei_misurati(tqc, layout, cal):
    """Readout medio dei qubit FISICI su cui cadono le misure: verifica che la
    manipolazione dei ruoli abbia davvero avuto effetto."""
    vals = []
    for inst in tqc.data:
        if inst.operation.name == 'measure':
            i = tqc.find_bit(inst.qubits[0]).index
            vals.append(cal['readout'][layout[i]])
    return float(np.mean(vals)) if vals else float('nan')


def valuta(qc, lay, cm, cal, init, shots, seed):
    tqc = transpile(qc, basis_gates=P.BASIS, coupling_map=cm, optimization_level=2,
                    initial_layout=init, seed_transpiler=seed)
    nm = P.noise_model_layout(lay, cal)
    ps = P.prob_successo(tqc, nm, shots, seed)
    return ps, readout_dei_misurati(tqc, lay, cal), int(tqc.count_ops().get('ecr', 0))


def main():
    ap = argparse.ArgumentParser(description='M11b — effetto del ruolo dei qubit')
    ap.add_argument('--sottografi', type=int, default=10)
    ap.add_argument('--shots', type=int, default=8192)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--casuali', type=int, default=2)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    backend = FakeSherbrooke()
    cal = P.leggi_calibrazione(backend)
    adj = P.coupling_non_orientata(cal)
    qc = P.shor_circuit(P.N, P.A, N_COUNT)

    subs = P.campiona_layout(adj, args.sottografi, P.N_QUBITS, rng)
    print(f"Backend: {backend.name} | sottografi fissati: {len(subs)} | "
          f"{args.shots} shot\n")
    print("  sg  strategia            readout misurati   P_success   ECR")
    print("  " + "-" * 62)

    righe = []
    for s, lay in enumerate(subs):
        cm = P.coupling_ridotta(lay, adj)
        # indici (nella mappa ridotta) ordinati per readout crescente del fisico
        ordine = sorted(range(len(lay)), key=lambda i: cal['readout'][lay[i]])
        strategie = {}
        # conteggio (virtuali 0..7) sui migliori; lavoro (8..11) sui peggiori
        init = [0] * len(lay)
        for v, phys in enumerate(ordine[:N_COUNT]):
            init[v] = phys
        for k, phys in enumerate(ordine[N_COUNT:]):
            init[N_COUNT + k] = phys
        strategie['conteggio-migliore'] = list(init)
        # conteggio sui peggiori; lavoro sui migliori
        init = [0] * len(lay)
        for v, phys in enumerate(ordine[N_WORK:]):
            init[v] = phys
        for k, phys in enumerate(ordine[:N_WORK]):
            init[N_COUNT + k] = phys
        strategie['conteggio-peggiore'] = list(init)
        strategie['transpiler'] = None
        for r in range(args.casuali):
            perm = list(range(len(lay)))
            rng.shuffle(perm)
            strategie[f'casuale-{r+1}'] = perm

        riga = {'sottografo': lay, 'strategie': {}}
        for nome, init in strategie.items():
            try:
                ps, ro, necr = valuta(qc, lay, cm, cal, init, args.shots, args.seed + s)
            except Exception as e:
                print(f"  {s:<3} {nome:<20} errore: {type(e).__name__}")
                continue
            riga['strategie'][nome] = {'P_success': ps, 'readout_misurati': ro, 'n_ecr': necr}
            print(f"  {s:<3} {nome:<20} {ro:.5f}           {ps:.4f}     {necr}", flush=True)
        righe.append(riga)
        print()

    # ---------------- sintesi appaiata ----------------
    def serie(nome):
        return np.array([r['strategie'][nome]['P_success'] for r in righe
                         if nome in r['strategie']])

    best, worst = serie('conteggio-migliore'), serie('conteggio-peggiore')
    tr = serie('transpiler')
    cas = np.array([v['P_success'] for r in righe for k, v in r['strategie'].items()
                    if k.startswith('casuale')])

    n = min(len(best), len(worst))
    diff = best[:n] - worst[:n]
    se = float(np.std(diff, ddof=1) / np.sqrt(n)) if n > 1 else float('nan')

    print("=" * 68)
    print("ESITO M11b")
    print("=" * 68)
    print(f"  sottografi validi                    : {n}")
    print(f"  P_success conteggio-MIGLIORE (media) : {best[:n].mean():.4f}")
    print(f"  P_success conteggio-PEGGIORE (media) : {worst[:n].mean():.4f}")
    print(f"  P_success transpiler         (media) : {tr.mean():.4f}" if len(tr) else "")
    print(f"  P_success casuale            (media) : {cas.mean():.4f}" if len(cas) else "")
    print(f"\n  differenza appaiata migliore-peggiore: {diff.mean():+.4f} "
          f"({diff.mean()*100:+.2f} p.p.)")
    print(f"  errore standard sulla differenza     : {se:.4f}")
    if se and se == se and se > 0:
        print(f"  rapporto t                           : {diff.mean()/se:+.2f}")
    print(f"  sottografi in cui MIGLIORE > PEGGIORE: {int((diff > 0).sum())}/{n}")

    if n > 1 and abs(diff.mean()) > 2 * se and diff.mean() > 0:
        flag = ("VERDE — assegnare il conteggio ai qubit a readout migliore produce un "
                "guadagno sistematico: l'ipotesi regge")
    elif n > 1 and abs(diff.mean()) <= 2 * se:
        flag = ("ROSSO — nessuna differenza sistematica: il ruolo dei qubit non conta "
                "quanto ipotizzato")
    else:
        flag = "ANOMALO — differenza sistematica ma di segno opposto all'atteso"
    print(f"\n  FLAG: {flag}")

    out = {'milestone': 'M11b_ruoli', 'timestamp': datetime.now().isoformat(),
           'backend': backend.name, 'shots': args.shots, 'seed': args.seed,
           'media_migliore': float(best[:n].mean()), 'media_peggiore': float(worst[:n].mean()),
           'media_transpiler': float(tr.mean()) if len(tr) else None,
           'media_casuale': float(cas.mean()) if len(cas) else None,
           'differenza_appaiata': float(diff.mean()), 'se': se,
           'n_favorevoli': int((diff > 0).sum()), 'n': int(n),
           'flag': flag, 'righe': righe}
    fn = f"results_M11b_ruoli_{datetime.now():%Y%m%d_%H%M%S}.json"
    json.dump(out, open(fn, 'w'), indent=2)
    print(f"\nRisultati salvati in: {fn}")


if __name__ == '__main__':
    main()
