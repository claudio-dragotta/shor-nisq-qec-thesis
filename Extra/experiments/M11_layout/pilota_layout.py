"""
pilota_layout.py — Milestone M11: il layout ottimo per la FEDELTA' e' anche quello ottimo
per la FATTORIZZAZIONE?

CONTESTO. La letteratura sulla scelta del layout (mapomatic, ranker appresi, surrogati LSTM)
ottimizza la FEDELTA' DEL CIRCUITO. Ma per Shor l'obiettivo non e' la fedelta': e' che escano
i fattori. Le due cose non coincidono per ragioni strutturali:
  - i qubit di CONTEGGIO portano la fase da cui si estrae il periodo: un errore li' e' fatale;
  - il registro di LAVORO viene scartato: un errore li' costa meno;
  - le frazioni continue hanno una banda di tolleranza: una fase spostata di poco funziona.

DOMANDA. Quanto correlano il punteggio di fedelta' (stile mapomatic, calcolato dai soli dati
di calibrazione, senza eseguire nulla) e la probabilita' di successo della fattorizzazione?
E quanto si perde scegliendo il layout ottimo secondo la fedelta' anziche' secondo il successo?

FLAG (piano_azione_layout_ml.md, M11):
  VERDE  correlazione bassa + perdita apprezzabile -> esiste un divario che solo la semantica
         dell'algoritmo puo' colmare
  GIALLO correlazione alta ma non piena
  ROSSO  i due ottimi coincidono -> la fedelta' e' un buon surrogato, mapomatic basta

DATI. Calibrazione REALE di ibm_sherbrooke via FakeSherbrooke (snapshot offline, nessuna
credenziale). Eterogeneita' misurata: readout 170x, errore ECR 288x, T2 185x fra il qubit
migliore e il peggiore. Senza questa eterogeneita' l'esperimento sarebbe nullo per costruzione.

Uso: ~/quantum-env/bin/python pilota_layout.py [--layouts 60] [--shots 8192]
"""
import argparse
import json
import os
import random
import sys
from datetime import datetime

import numpy as np
from qiskit import transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import (NoiseModel, ReadoutError, depolarizing_error, pauli_error,
                              thermal_relaxation_error)  # noqa: F401
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'campagne_classiche_M1-M4'))
from shor_core import shor_circuit, extract_factors          # noqa: E402

N, A, N_COUNT = 15, 7, 8
N_QUBITS = N_COUNT + 4          # 8 conteggio + 4 lavoro = 12
BASIS = ['sx', 'rz', 'x', 'ecr']


# --------------------------------------------------------------------- calibrazione
def leggi_calibrazione(backend):
    """Estrae dal target i parametri per-qubit e per-arco che servono."""
    t = backend.target
    cal = {'readout': {}, 'sx_err': {}, 't1': {}, 't2': {}, 'ecr': {}, 'sx_dur': {}}
    for q in range(backend.num_qubits):
        m = t['measure'].get((q,))
        cal['readout'][q] = m.error if m and m.error is not None else 0.0
        s = t['sx'].get((q,))
        cal['sx_err'][q] = s.error if s and s.error is not None else 0.0
        cal['sx_dur'][q] = s.duration if s and s.duration else 5e-8
        qp = t.qubit_properties[q]
        cal['t1'][q] = qp.t1 or 1.0
        cal['t2'][q] = qp.t2 or 1.0
    for (a, b), props in t['ecr'].items():
        if props is not None and props.error is not None:
            cal['ecr'][(a, b)] = props.error
    return cal


def coupling_non_orientata(cal):
    adj = {}
    for (a, b) in cal['ecr']:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    return adj


# --------------------------------------------------------------------- layout
def campiona_layout(adj, k, n_qubit, rng):
    """k sottografi connessi di n_qubit qubit, campionati per crescita casuale."""
    nodi = sorted(adj)
    visti, out = set(), []
    tentativi = 0
    while len(out) < k and tentativi < k * 200:
        tentativi += 1
        start = rng.choice(nodi)
        scelti = [start]
        frontiera = set(adj[start])
        while len(scelti) < n_qubit and frontiera:
            q = rng.choice(sorted(frontiera))
            scelti.append(q)
            frontiera |= adj[q]
            frontiera -= set(scelti)
        if len(scelti) < n_qubit:
            continue
        chiave = tuple(sorted(scelti))
        if chiave in visti:
            continue
        visti.add(chiave)
        out.append(scelti)          # ordine = assegnazione virtuale->fisico
    return out


def coupling_ridotta(layout, adj):
    """Archi interni al layout, rietichettati 0..n-1 (entrambe le direzioni)."""
    idx = {q: i for i, q in enumerate(layout)}
    cm = []
    for q in layout:
        for v in adj[q]:
            if v in idx:
                cm.append([idx[q], idx[v]])
    return cm


# --------------------------------------------------------------------- rumore
def rilassamento_pauli(t1, t2, dur):
    """Approssimazione di Pauli (twirl) del rilassamento termico.

    Aer va in corruzione di memoria quando un errore di Kraus non-Pauli
    (thermal_relaxation_error) convive con errori depolarizzanti a due qubit sullo stesso
    modello, su circuiti di questa profondita'. Poiche' l'intera tesi adotta comunque modelli
    di Pauli --- e la Sez. 12.6 ne discute esplicitamente i limiti --- si usa qui il canale di
    Pauli equivalente, che riproduce le stesse probabilita' marginali di errore:

        p_x = p_y = (1 - e^{-t/T1}) / 4
        p_z     = (1 - e^{-t/T2}) / 2 - p_x

    Verifiche di consistenza: con T2 = 2*T1 (solo rilassamento) si ottiene p_z = 0;
    con T2 << T1 (solo defasamento) si ottiene p_x = p_y = 0.
    """
    p_reset = 1.0 - np.exp(-dur / max(t1, 1e-12))
    p_xy = p_reset / 4.0
    p_z = max((1.0 - np.exp(-dur / max(t2, 1e-12))) / 2.0 - p_xy, 0.0)
    p_i = max(1.0 - 2 * p_xy - p_z, 0.0)
    return pauli_error([('X', p_xy), ('Y', p_xy), ('Z', p_z), ('I', p_i)])


def noise_model_layout(layout, cal):
    """Noise model sui soli qubit del layout, con i parametri REALI di quei qubit fisici."""
    nm = NoiseModel(basis_gates=BASIS)
    idx = {q: i for i, q in enumerate(layout)}
    for q, i in idx.items():
        # depolarizzante e rilassamento vanno COMPOSTI in un unico errore: registrarli
        # separatamente sulla stessa istruzione fa accodare gli errori ad Aer.
        t1, t2, dur = cal['t1'][q], min(cal['t2'][q], 2 * cal['t1'][q]), cal['sx_dur'][q]
        err = rilassamento_pauli(t1, t2, dur)
        e = cal['sx_err'][q]
        if e > 0:
            err = depolarizing_error(min(e, 0.75), 1).compose(err)
        nm.add_quantum_error(err, ['sx', 'x'], [i])
        p = min(max(cal['readout'][q], 0.0), 0.5)
        nm.add_readout_error(ReadoutError([[1 - p, p], [p, 1 - p]]), [i])
    for (a, b), err in cal['ecr'].items():
        if a in idx and b in idx:
            nm.add_quantum_error(depolarizing_error(min(err, 0.99), 2), ['ecr'],
                                 [idx[a], idx[b]])
    return nm


# --------------------------------------------------------------------- punteggio fedelta'
def punteggio_fedelta(tqc, layout, cal):
    """Stile mapomatic: s = 1 - prod(1 - e_x) su gate e misure effettivamente usati.
    Calcolato dai SOLI dati di calibrazione, senza eseguire il circuito."""
    idx_inv = {i: q for i, q in enumerate(layout)}
    fid = 1.0
    for inst in tqc.data:
        nome = inst.operation.name
        qs = [idx_inv[tqc.find_bit(q).index] for q in inst.qubits]
        if nome == 'ecr' and len(qs) == 2:
            e = cal['ecr'].get((qs[0], qs[1]), cal['ecr'].get((qs[1], qs[0]), 0.0))
        elif nome in ('sx', 'x'):
            e = cal['sx_err'].get(qs[0], 0.0)
        elif nome == 'measure':
            e = cal['readout'].get(qs[0], 0.0)
        else:
            continue                       # rz e' virtuale: errore nullo
        fid *= (1 - e)
    return 1 - fid                          # punteggio: piu' basso = meglio


# --------------------------------------------------------------------- successo
def prob_successo(tqc, nm, shots, seed):
    sim = AerSimulator(noise_model=nm, method='statevector')
    counts = sim.run(tqc, shots=shots, seed_simulator=seed).result().get_counts()
    ok = 0
    for bit, n in counts.items():
        val = int(bit.replace(' ', ''), 2)
        p, q = extract_factors(val, N_COUNT, N, A)
        if p is not None:
            ok += n
    return ok / shots


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="M11 — pilota fedelta' vs successo")
    ap.add_argument('--layouts', type=int, default=60)
    ap.add_argument('--shots', type=int, default=8192)
    ap.add_argument('--seed', type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    backend = FakeSherbrooke()
    cal = leggi_calibrazione(backend)
    adj = coupling_non_orientata(cal)
    print(f"Backend: {backend.name} ({backend.num_qubits} qubit), calibrazione reale")

    layouts = campiona_layout(adj, args.layouts, N_QUBITS, rng)
    print(f"Layout campionati: {len(layouts)} (sottografi connessi da {N_QUBITS} qubit)\n")

    qc = shor_circuit(N, A, N_COUNT)
    righe = []
    print("  #   qubit fisici (primi 6)   punteggio_fed   P_success   CX")
    print("  " + "-" * 66)
    for i, lay in enumerate(layouts):
        cm = coupling_ridotta(lay, adj)
        try:
            tqc = transpile(qc, basis_gates=BASIS, coupling_map=cm,
                            optimization_level=3, seed_transpiler=args.seed + i)
        except Exception as e:
            print(f"  {i:<3} transpile fallita: {type(e).__name__}")
            continue
        s = punteggio_fedelta(tqc, lay, cal)
        nm = noise_model_layout(lay, cal)
        ps = prob_successo(tqc, nm, args.shots, args.seed + i)
        necr = tqc.count_ops().get('ecr', 0)
        righe.append({'layout': lay, 'punteggio_fedelta': s, 'P_success': ps,
                      'n_ecr': int(necr), 'depth': int(tqc.depth())})
        print(f"  {i:<3} {str(lay[:6]):<24} {s:.6f}      {ps:.4f}     {necr}", flush=True)

    if len(righe) < 5:
        print("\nTroppi pochi layout validi: impossibile concludere.")
        return

    sc = np.array([r['punteggio_fedelta'] for r in righe])
    pw = np.array([r['P_success'] for r in righe])

    # correlazioni: punteggio BASSO dovrebbe corrispondere a P_success ALTA -> attesa negativa
    pear = float(np.corrcoef(sc, pw)[0, 1])
    rs = np.argsort(np.argsort(sc)); rp = np.argsort(np.argsort(pw))
    spear = float(np.corrcoef(rs, rp)[0, 1])

    i_fed = int(np.argmin(sc))       # migliore secondo la fedelta'
    i_suc = int(np.argmax(pw))       # migliore davvero
    perdita = float(pw[i_suc] - pw[i_fed])

    print("\n" + "=" * 70)
    print("ESITO M11")
    print("=" * 70)
    print(f"  layout valutati                 : {len(righe)}")
    print(f"  P_success  min / mediana / max  : {pw.min():.4f} / {np.median(pw):.4f} / {pw.max():.4f}")
    print(f"  forbice (max-min)               : {pw.max()-pw.min():.4f}")
    print(f"  correlazione di Pearson         : {pear:+.3f}   (attesa negativa e forte)")
    print(f"  correlazione di Spearman        : {spear:+.3f}")
    print(f"  P_success del layout migliore per FEDELTA' : {pw[i_fed]:.4f}")
    print(f"  P_success del layout migliore in ASSOLUTO  : {pw[i_suc]:.4f}")
    print(f"  --> PERDITA usando la metrica di fedelta'  : {perdita:.4f} ({perdita*100:.2f} p.p.)")

    if spear > -0.5 and perdita < 0.02:
        flag = "ROSSO — i due ottimi sostanzialmente coincidono: la fedelta' e' un buon surrogato"
    elif spear <= -0.5 and perdita < 0.02:
        flag = "ROSSO/GIALLO — correlazione forte e perdita piccola: margine sottile"
    elif spear > -0.5 and perdita >= 0.02:
        flag = "VERDE — la fedelta' predice male E si perde successo: esiste il divario cercato"
    else:
        flag = "GIALLO — correlazione forte ma perdita non trascurabile"
    print(f"\n  FLAG: {flag}")

    out = {'milestone': 'M11_pilota_layout', 'timestamp': datetime.now().isoformat(),
           'backend': backend.name, 'N': N, 'a': A, 'n_count': N_COUNT,
           'shots': args.shots, 'seed': args.seed, 'n_layout': len(righe),
           'pearson': pear, 'spearman': spear,
           'P_success_best_by_fidelity': float(pw[i_fed]),
           'P_success_best_overall': float(pw[i_suc]),
           'perdita_metrica_sbagliata': perdita, 'flag': flag, 'punti': righe}
    fn = f"results_M11_pilota_{datetime.now():%Y%m%d_%H%M%S}.json"
    json.dump(out, open(fn, 'w'), indent=2)
    print(f"\nRisultati salvati in: {fn}")


if __name__ == '__main__':
    main()
