"""
qec_neural_decoder.py — Milestone M10: decodifica appresa vs MWPM sul surface code.

Chiude il cerchio della tesi. Il ML applicato a VALLE dell'esecuzione non serve (Cap. 10:
l'ablazione mostra che il guadagno e' tutto del TOP-4); applicato alla SINDROME — dove
l'informazione strutturale c'e' ancora — e' un'altra cosa. E' anche l'esperimento che rende
vera in tesi l'affermazione del Cap. 6 ("il modello apprenditivo sostituisce il decoder
analitico"), oggi solo dichiarata: la parte QEC usa MWPM, cioe' un decoder analitico.

Il dataset e' gia' prodotto da Stim, senza infrastruttura aggiuntiva:
    det, obs = sampler.sample(shots, separate_observables=True)
    -> X = det (detection events = sindrome), y = obs (flip logico)
Lo stimatore e' lo STESSO strumento del classificatore bocciato in Cap. 10 (MLP di
scikit-learn): cambia il punto della pipeline in cui viene applicato, non la tecnologia.

TRE ESPERIMENTI

  E1  CONFRONTO LEALE — rumore circuit-level uniforme, MWPM riceve il DEM ESATTO.
      A parita' di informazione la rete impara qualcosa che il matching scarta (la
      degenerazione: MWPM sceglie il matching di peso minimo, non somma sulle classi di
      errore equivalenti)? E1b misura come il risultato scala col volume di dati.

  E2  RUMORE CORRELATO (CROSSTALK) — il caso in cui il modello del decoder e' strutturalmente
      sbagliato, non solo mal calibrato. Un accoppiamento capacitivo residuo fra qubit dati
      adiacenti (quarta fonte di rumore del Cap. 5) produce errori a due qubit correlati: il
      grafo di matching non ha alcun arco per rappresentarli. Tre bracci:
        - MWPM con il DEM nominale (cio' che l'operatore crede: rumore uniforme)
        - MWPM con il DEM del circuito reale ("oracolo": conosce il crosstalk)
        - rete addestrata sui campioni reali
      E' la gamba sperimentale della Sez. 12.6 "Oltre il modello di Pauli", oggi solo discussa.

  E3  CONFERMA/SMENTITA DELLA CORREZIONE (richiesta esplicita del relatore, 2026-07-08:
      "una rete che confermi o neghi la correzione fatta dal circuito ancillare"): la
      probabilita' in uscita dalla rete usata come flag di confidenza sulla risposta di MWPM.

RIPRODUCIBILITA': ogni configurazione ha un seed deterministico passato SIA al campionatore
Stim SIA alla rete. (In M7 il seed era dichiarato nel JSON ma mai passato a
compile_detector_sampler: le curve del Cap. 12 non sono rigenerabili bit per bit.)

Uso (WSL, quantum-env con stim + pymatching + scikit-learn):
    ~/quantum-env/bin/python qec_neural_decoder.py
    ~/quantum-env/bin/python qec_neural_decoder.py --shots 100000 --only e2
"""
import argparse
import json
import time
from datetime import datetime

import numpy as np
import stim
import pymatching
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import roc_auc_score

# ----------------------------------------------------------------------------- parametri
BASIS = 'z'
P_PHYS = 0.003                                   # sotto la soglia misurata in M7 (~0.9%)
P_LIST_E1 = [0.002, 0.003, 0.004, 0.005, 0.006, 0.008, 0.010]
N_TRAIN_E1B = [25_000, 50_000, 100_000, 300_000, 800_000]
PCT_LIST_E2 = [0.005, 0.010, 0.020, 0.040]       # intensita' del crosstalk
TRAIN_FRAC = 0.75


# ----------------------------------------------------------------------------- circuiti
def build_circuit(d, p, basis=BASIS, rounds=None):
    """Surface code ruotato, memory experiment, rumore circuit-level (come in M7)."""
    return stim.Circuit.generated(
        f'surface_code:rotated_memory_{basis}',
        distance=d,
        rounds=rounds or d,
        after_clifford_depolarization=p,
        after_reset_flip_probability=p,
        before_measure_flip_probability=p,
    )


def data_neighbour_pairs(circuit):
    """Coppie di qubit DATI fisicamente adiacenti sulla griglia.

    Nel layout ruotato di Stim i qubit di misura stanno fra i dati, quindi due dati adiacenti
    distano 2 in coordinate. Sono le coppie su cui un accoppiamento capacitivo residuo
    produce crosstalk. I qubit di misura sono quelli del PRIMO MR (estrazione di sindrome):
    l'ultima misura del memory experiment legge anche i dati, quindi non e' discriminante.
    """
    coords = circuit.get_final_qubit_coordinates()
    ancillas = set()
    for inst in circuit.flattened():
        if inst.name in ('MR', 'MRX'):
            ancillas = {t.qubit_value for t in inst.targets_copy()}
            break
    data = {q: tuple(c) for q, c in coords.items() if q not in ancillas}
    pairs = []
    for qa, ca in sorted(data.items()):
        for qb, cb in sorted(data.items()):
            if qa < qb and {abs(ca[0] - cb[0]), abs(ca[1] - cb[1])} == {0, 2}:
                pairs += [qa, qb]
    return pairs


def _inject(block, pairs, p_ct):
    """Inserisce un DEPOLARIZE2 correlato sui dati una volta per ciclo di sindrome.

    L'inizio di ogni ciclo e' marcato dal DEPOLARIZE1 che segue le H sui qubit di misura;
    ce ne sono due per ciclo, quindi un toggle individua il primo. La ricorsione tratta il
    blocco REPEAT con cui Stim rappresenta i cicli intermedi.
    """
    out = stim.Circuit()
    first = True
    for inst in block:
        if isinstance(inst, stim.CircuitRepeatBlock):
            out += _inject(inst.body_copy(), pairs, p_ct) * inst.repeat_count
            continue
        out.append(inst)
        if inst.name == 'DEPOLARIZE1':
            if first:
                out.append('DEPOLARIZE2', pairs, p_ct)
            first = not first
    return out


def with_crosstalk(circuit, p_ct):
    """Circuito 'reale' con crosstalk fra dati adiacenti (p_ct=0 -> circuito invariato)."""
    if p_ct <= 0:
        return circuit
    return _inject(circuit, data_neighbour_pairs(circuit), p_ct)


# ----------------------------------------------------------------------------- decoder
def sample(circuit, shots, seed):
    det, obs = circuit.compile_detector_sampler(seed=seed).sample(
        shots, separate_observables=True)
    return det, obs[:, 0]


def matcher(circuit):
    dem = circuit.detector_error_model(decompose_errors=True)
    return pymatching.Matching.from_detector_error_model(dem)


def mwpm_predict(matching, det):
    return matching.decode_batch(det)[:, 0].astype(bool)


def train_nn(det_tr, y_tr, seed):
    nn = MLPClassifier(
        hidden_layer_sizes=(128, 64),
        activation='relu',
        alpha=1e-5,
        batch_size=4096,
        learning_rate_init=3e-3,
        max_iter=200,
        early_stopping=True,
        n_iter_no_change=10,
        validation_fraction=0.1,
        random_state=seed,
    )
    nn.fit(det_tr.astype(np.float32), y_tr)
    return nn


def binom_se(pL, n):
    return float((pL * (1 - pL) / n) ** 0.5)


# ----------------------------------------------------------------------------- runner
def run_config(d, p, shots, seed, p_ct=0.0, n_train=None, want_oracle=False):
    """Campiona, decodifica con MWPM, addestra la rete, confronta sullo stesso test set."""
    t0 = time.time()
    circ_nom = build_circuit(d, p)
    circ_real = with_crosstalk(circ_nom, p_ct)

    det, y = sample(circ_real, shots, seed)
    n_tr = n_train if n_train is not None else int(shots * TRAIN_FRAC)
    det_tr, y_tr = det[:n_tr], y[:n_tr]
    det_te, y_te = det[n_tr:], y[n_tr:]
    n_te = len(y_te)

    # MWPM con il DEM che l'operatore crede (rumore uniforme, senza crosstalk)
    pred_mwpm = mwpm_predict(matcher(circ_nom), det_te)
    pL_mwpm = float((pred_mwpm != y_te).mean())

    res = {
        'd': d, 'p': p, 'p_crosstalk': p_ct, 'shots': shots, 'seed': seed,
        'n_detectors': int(det.shape[1]), 'n_train': int(n_tr), 'n_test': int(n_te),
        'base_rate': float(y.mean()),          # p_L di un decoder banale ("non correggo")
        'pL_mwpm': pL_mwpm, 'pL_mwpm_se': binom_se(pL_mwpm, n_te),
    }

    # MWPM "oracolo": conosce il crosstalk (DEM del circuito reale)
    if want_oracle and p_ct > 0:
        try:
            pred_or = mwpm_predict(matcher(circ_real), det_te)
            pL_or = float((pred_or != y_te).mean())
            res['pL_mwpm_oracle'] = pL_or
            res['pL_mwpm_oracle_se'] = binom_se(pL_or, n_te)
        except Exception as e:
            res['pL_mwpm_oracle'] = None
            res['oracle_error'] = f'{type(e).__name__}: {e}'

    # decoder neurale
    nn = train_nn(det_tr, y_tr, seed)
    proba = nn.predict_proba(det_te.astype(np.float32))[:, 1]
    pred_nn = proba >= 0.5
    pL_nn = float((pred_nn != y_te).mean())
    res.update({
        'pL_nn': pL_nn, 'pL_nn_se': binom_se(pL_nn, n_te),
        'gain_vs_mwpm': (pL_mwpm / pL_nn) if pL_nn > 0 else None,
        'nn_epochs': int(nn.n_iter_), 'secs': round(time.time() - t0, 1),
    })
    res['_arrays'] = {'proba': proba, 'pred_mwpm': pred_mwpm, 'y_te': y_te}
    return res


def fmt(r):
    s = (f"  d={r['d']} p={r['p']:<6g} p_ct={r['p_crosstalk']:<6g} "
         f"tr={r['n_train']:>7d}  banale={r['base_rate']:.4f}  "
         f"MWPM={r['pL_mwpm']:.5f}  NN={r['pL_nn']:.5f}")
    if r.get('pL_mwpm_oracle') is not None:
        s += f"  oracolo={r['pL_mwpm_oracle']:.5f}"
    if r['gain_vs_mwpm']:
        s += f"  |  NN/MWPM={r['gain_vs_mwpm']:.2f}x"
    s += f"  [{r['secs']}s]"
    return s


def strip(r):
    return {k: v for k, v in r.items() if k != '_arrays'}


def significant_win(r):
    """La rete batte MWPM oltre 2 sigma combinati?"""
    se = (r['pL_nn_se'] ** 2 + r['pL_mwpm_se'] ** 2) ** 0.5
    return r['pL_nn'] < r['pL_mwpm'] - 2 * se


# ----------------------------------------------------------------------------- E1
def exp1(distances, shots):
    print("\n" + "=" * 78)
    print("E1 — CONFRONTO LEALE (MWPM con DEM esatto, rumore uniforme)")
    print("Domanda: a parita' di informazione la rete recupera cio' che il matching scarta?")
    print("=" * 78)
    out = []
    for d in distances:
        for i, p in enumerate(P_LIST_E1):
            r = run_config(d, p, shots, seed=1000 + d * 100 + i)
            print(fmt(r), flush=True)
            out.append(strip(r))
    wins = sum(1 for r in out if significant_win(r))
    print(f"\nFLAG E1: la rete batte MWPM (oltre 2 sigma) in {wins}/{len(out)} configurazioni")
    return {'points': out, 'nn_wins_2sigma': wins, 'n_configs': len(out)}


def exp1b(d, shots):
    print("\n" + "=" * 78)
    print(f"E1b — SCALING COL VOLUME DI DATI (d={d}, p={P_PHYS})")
    print("Quanto della distanza da MWPM e' fame di dati?")
    print("=" * 78)
    out = []
    for i, ntr in enumerate(N_TRAIN_E1B):
        if ntr + 100_000 > shots:
            print(f"  (salto n_train={ntr}: servono piu' shot)")
            continue
        r = run_config(d, P_PHYS, shots, seed=1500 + i, n_train=ntr)
        print(fmt(r), flush=True)
        out.append(strip(r))
    return {'d': d, 'p': P_PHYS, 'points': out}


# ----------------------------------------------------------------------------- E2
def exp2(distances, shots):
    print("\n" + "=" * 78)
    print("E2 — RUMORE CORRELATO (CROSSTALK): il modello del decoder e' STRUTTURALMENTE")
    print(f"    sbagliato, non solo mal calibrato. p fisico = {P_PHYS}.")
    print("=" * 78)
    out, keep = [], None
    for d in distances:
        # riferimento senza crosstalk
        r0 = run_config(d, P_PHYS, shots, seed=2000 + d * 100)
        print(fmt(r0), flush=True)
        out.append(strip(r0))
        for i, pct in enumerate(PCT_LIST_E2):
            r = run_config(d, P_PHYS, shots, seed=2000 + d * 100 + i + 1,
                           p_ct=pct, want_oracle=True)
            print(fmt(r), flush=True)
            if d == distances[0] and pct == 0.010:
                keep = r                      # configurazione per E3
            out.append(strip(r))
    wins = sum(1 for r in out if r['p_crosstalk'] > 0 and significant_win(r))
    tot = sum(1 for r in out if r['p_crosstalk'] > 0)
    print(f"\nFLAG E2: la rete batte MWPM (oltre 2 sigma) in {wins}/{tot} configurazioni "
          f"con crosstalk")
    return {'points': out, 'p': P_PHYS, 'pct_list': PCT_LIST_E2,
            'nn_wins_2sigma': wins, 'n_configs': tot}, keep


# ----------------------------------------------------------------------------- E3
def exp3(r):
    """La rete come validatore della correzione MWPM.

    confidenza = probabilita' che la rete assegna ALLA RISPOSTA DATA DA MWPM.
    Bassa confidenza = "la rete nega la correzione". Si misura quanto bene il flag
    individua gli shot in cui MWPM ha effettivamente sbagliato.
    """
    print("\n" + "=" * 78)
    print("E3 — LA RETE CONFERMA O NEGA LA CORREZIONE DI MWPM")
    print("=" * 78)
    a = r['_arrays']
    proba, pred_mwpm, y_te = a['proba'], a['pred_mwpm'], a['y_te']

    conf = np.where(pred_mwpm, proba, 1.0 - proba)
    err = (pred_mwpm != y_te)
    auc = float(roc_auc_score(err, 1.0 - conf)) if err.any() and not err.all() else None

    rows = []
    for thr in (0.5, 0.3, 0.2, 0.1):
        flag = conf < thr
        tp = int((flag & err).sum())
        prec = tp / int(flag.sum()) if flag.sum() else 0.0
        rec = tp / int(err.sum()) if err.sum() else 0.0
        rows.append({'soglia': thr, 'flag_rate': float(flag.mean()),
                     'precision': prec, 'recall': rec})
        print(f"  soglia {thr:<4}: segnala {flag.mean()*100:5.2f}% degli shot | "
              f"precision {prec:.3f} | recall {rec:.3f}", flush=True)

    print(f"\n  AUC del flag nel predire 'MWPM sbaglia': "
          + (f"{auc:.4f}" if auc else "non calcolabile"))
    print(f"  configurazione: d={r['d']}, p={r['p']}, crosstalk={r['p_crosstalk']}, "
          f"errori MWPM nel test set: {int(err.sum())}/{len(err)}")
    return {'config': {'d': r['d'], 'p': r['p'], 'p_crosstalk': r['p_crosstalk']},
            'auc_flag': auc, 'n_mwpm_errors': int(err.sum()), 'n_test': int(len(err)),
            'soglie': rows}


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="M10 — decoder neurale vs MWPM")
    ap.add_argument('--shots', type=int, default=400_000)
    ap.add_argument('--shots-scaling', type=int, default=900_000)
    ap.add_argument('--distances', type=int, nargs='+', default=[3, 5])
    ap.add_argument('--only', choices=['e1', 'e1b', 'e2', 'all'], default='all')
    args = ap.parse_args()

    t0 = time.time()
    out = {'milestone': 'M10_neural_decoder', 'timestamp': datetime.now().isoformat(),
           'basis': BASIS, 'shots_per_config': args.shots, 'distances': args.distances,
           'train_frac': TRAIN_FRAC, 'p_phys': P_PHYS,
           'nn': 'MLPClassifier(128,64) relu, batch 4096, early_stopping',
           'stim': stim.__version__, 'pymatching': pymatching.__version__}

    if args.only in ('e1', 'all'):
        out['E1_leale'] = exp1(args.distances, args.shots)
    if args.only in ('e1b', 'all'):
        out['E1b_scaling'] = exp1b(args.distances[0], args.shots_scaling)
    if args.only in ('e2', 'all'):
        e2, keep = exp2(args.distances, args.shots)
        out['E2_crosstalk'] = e2
        if keep is not None:
            out['E3_validatore'] = exp3(keep)

    fname = f"results_M10_neural_decoder_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(fname, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nTempo totale: {(time.time()-t0)/60:.1f} min")
    print(f"Risultati salvati in: {fname}")


if __name__ == '__main__':
    main()
