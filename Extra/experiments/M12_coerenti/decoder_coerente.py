"""
decoder_coerente.py — M12: il decoder appreso guadagna DI PIU' sugli errori coerenti?

LA PREVISIONE CHE SI METTE ALLA PROVA. Il criterio del Cap. 15, precisato dall'Appendice G,
dice che un modello appreso rende quando (a) il metodo esistente e' strutturalmente cieco a
una classe di informazione e (b) quell'informazione e' sfruttabile senza costi compensativi.
Gli errori coerenti soddisfano entrambe le condizioni PIU' FORTEMENTE del crosstalk di Pauli
gia' studiato nella Sez. 12.7:

  (a) il MWPM non e' "mal calibrato" sugli errori coerenti: e' costruito su un modello di
      Pauli, e una sovrarotazione coerente NON e' un errore di Pauli. La cecita' e' totale,
      non parziale. Le ampiezze si sommano (accumulo quadratico), le probabilita' no.
  (b) la rete legge la stessa sindrome e agisce dopo la decodifica: non tocca il circuito,
      quindi nessun costo compensativo (a differenza del layout, Appendice G).

PREVISIONE FALSIFICABILE: il guadagno del decoder appreso dev'essere MAGGIORE sotto errori
coerenti che sotto errori di Pauli di pari probabilita' marginale.

PERCHE' NON SI PUO' USARE STIM. Stim e' un simulatore a stabilizzatori: rappresenta solo
errori di Pauli. Simulare una sovrarotazione coerente richiede un simulatore full-state, ed
e' precisamente questa impossibilita' a rendere l'esperimento interessante.

SISTEMA. Surface code ruotato d=3, memory Z: 9 qubit dati + 4 ancilla per gli stabilizzatori
di tipo Z (che rilevano gli errori X). Le sovrarotazioni RX sono errori di tipo X, quindi il
codice rileva esattamente la classe di errore iniettata.

  dati (griglia 3x3)        stabilizzatori Z        osservabile logico
     0 1 2                  Za = {0,1,3,4}          Z_L = Z0 Z1 Z2
     3 4 5                  Zb = {4,5,7,8}
     6 7 8                  Zc = {2,5}
                            Zd = {3,6}

CONFRONTO A PARITA' DI PROBABILITA' MARGINALE:
  Pauli    : X con probabilita' p su ogni qubit dato, a ogni ciclo
  Coerente : RX(theta) con sin^2(theta/2) = p  -> stessa probabilita' di flip in un ciclo,
             ma le ampiezze si accumulano fra un ciclo e l'altro invece delle probabilita'

Il MWPM riceve in ENTRAMBI i casi i pesi del modello di Pauli: e' cio' che un operatore ha.

Uso: ~/quantum-env/bin/python decoder_coerente.py [--shots 40000]
"""
import argparse
import json
import math
from datetime import datetime

import numpy as np
import pymatching
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, ReadoutError, pauli_error
from sklearn.metrics import roc_auc_score
from sklearn.neural_network import MLPClassifier

# ------------------------------------------------------------------ geometria del codice
ZSTAB = [[0, 1, 3, 4], [4, 5, 7, 8], [2, 5], [3, 6]]   # stabilizzatori di tipo Z
LOGICO = [0, 1, 2]                                      # Z_L = Z0 Z1 Z2 (riga superiore)
N_DATA, N_ANC = 9, 4


def build_circuit(rounds, p, modo, p_meas):
    """Memory-Z del surface code d=3. I dati partono da |0>: gli stabilizzatori Z e Z_L
    hanno esito deterministico, quindi ogni deviazione e' un errore rivelato."""
    d = QuantumRegister(N_DATA, 'd')
    a = QuantumRegister(N_ANC, 'a')
    cs = [ClassicalRegister(N_ANC, f's{t}') for t in range(rounds)]
    cd = ClassicalRegister(N_DATA, 'dm')
    qc = QuantumCircuit(d, a, *cs, cd)

    theta = 2 * math.asin(math.sqrt(p)) if p > 0 else 0.0
    for t in range(rounds):
        # --- iniezione dell'errore sui dati ---
        for q in range(N_DATA):
            if modo == 'coerente':
                if theta:
                    qc.rx(theta, d[q])       # unitario: le ampiezze si accumulano
            else:
                qc.id(d[q])                  # aggancio per l'errore di Pauli del noise model
        qc.barrier()
        # --- estrazione della sindrome di tipo Z ---
        for k, sup in enumerate(ZSTAB):
            for q in sup:
                qc.cx(d[q], a[k])
        for k in range(N_ANC):
            qc.measure(a[k], cs[t][k])
            qc.reset(a[k])
        qc.barrier()
    qc.measure(d, cd)
    return qc


def noise_model(p, modo, p_meas):
    nm = NoiseModel(basis_gates=['id', 'rx', 'cx', 'x'])
    if modo == 'pauli' and p > 0:
        err = pauli_error([('X', p), ('I', 1 - p)])
        for q in range(N_DATA):          # errore a 1 qubit: va registrato per ciascun dato
            nm.add_quantum_error(err, ['id'], [q])
    if p_meas > 0:                       # errore di lettura sulle ancilla, in ENTRAMBI i modi
        for k in range(N_ANC):
            nm.add_readout_error(ReadoutError([[1 - p_meas, p_meas], [p_meas, 1 - p_meas]]),
                                 [N_DATA + k])
    return nm


# ------------------------------------------------------------------ detector e osservabile
def estrai(memoria, rounds):
    """Da una stringa di misura ai detection events + flip dell'osservabile logico.

    Qiskit concatena i registri classici dal PIU' RECENTE al piu' vecchio, separati da spazi:
        'dm s{r-1} ... s1 s0'
    Detector: differenza fra sindromi consecutive; l'ultimo strato confronta la sindrome
    ricostruita dalla misura finale dei dati con quella dell'ultimo ciclo.
    """
    parti = memoria.split()
    dm = parti[0][::-1]                                  # bit del qubit 0 in testa
    sind = [parti[1 + i][::-1] for i in range(rounds)]   # parti[1] = ultimo ciclo
    sind = sind[::-1]                                    # ordine cronologico

    s = [[int(sind[t][k]) for k in range(N_ANC)] for t in range(rounds)]
    dati = [int(dm[q]) for q in range(N_DATA)]
    s_fin = [sum(dati[q] for q in sup) % 2 for sup in ZSTAB]

    det = []
    for t in range(rounds):
        prec = s[t - 1] if t > 0 else [0] * N_ANC
        det += [s[t][k] ^ prec[k] for k in range(N_ANC)]
    det += [s_fin[k] ^ s[rounds - 1][k] for k in range(N_ANC)]

    obs = sum(dati[q] for q in LOGICO) % 2
    return det, obs


def build_matching(rounds, p, p_meas):
    """Grafo di matching con i pesi del modello di PAULI — cio' di cui il decoder dispone.

    Archi spaziali : un errore X sul dato q, allo strato t, accende gli stabilizzatori Z che
                     contengono q. Se sono due -> arco fra i due nodi; se e' uno solo ->
                     arco al bordo. L'arco commuta con l'osservabile se q sta in Z_L.
    Archi temporali: un errore di lettura sullo stabilizzatore k al ciclo t accende i
                     detector (k,t) e (k,t+1).
    """
    m = pymatching.Matching()
    nodo = lambda k, t: t * N_ANC + k
    n_strati = rounds + 1
    w_sp = math.log((1 - p) / p) if 0 < p < 1 else 20.0
    w_tm = math.log((1 - p_meas) / p_meas) if 0 < p_meas < 1 else 20.0

    for t in range(n_strati):
        for q in range(N_DATA):
            st = [k for k, sup in enumerate(ZSTAB) if q in sup]
            fid = {0} if q in LOGICO else set()
            if len(st) == 2:
                m.add_edge(nodo(st[0], t), nodo(st[1], t), fault_ids=fid, weight=w_sp,
                           merge_strategy='independent')
            elif len(st) == 1:
                m.add_boundary_edge(nodo(st[0], t), fault_ids=fid, weight=w_sp,
                                    merge_strategy='independent')
    for t in range(rounds):
        for k in range(N_ANC):
            m.add_edge(nodo(k, t), nodo(k, t + 1), fault_ids=set(), weight=w_tm,
                       merge_strategy='independent')
    return m


# ------------------------------------------------------------------ campionamento
def campiona(rounds, p, modo, p_meas, shots, seed):
    qc = build_circuit(rounds, p, modo, p_meas)
    sim = AerSimulator(noise_model=noise_model(p, modo, p_meas), method='statevector')
    counts = sim.run(qc, shots=shots, seed_simulator=seed).result().get_counts()
    det, obs = [], []
    for mem, n in counts.items():
        dd, oo = estrai(mem, rounds)
        det += [dd] * n
        obs += [oo] * n
    det = np.array(det, dtype=np.uint8)
    obs = np.array(obs, dtype=np.uint8)
    # MESCOLARE E' OBBLIGATORIO: get_counts() restituisce gli esiti RAGGRUPPATI per stringa
    # di misura, quindi campioni identici finiscono adiacenti. Senza mescolamento lo split
    # train/test cadrebbe fra pattern di sindrome disgiunti invece che su un campione
    # casuale, e sia la rete sia la stima di p_L del matching risulterebbero distorte.
    perm = np.random.default_rng(seed).permutation(len(obs))
    return det[perm], obs[perm]


def train_nn(X, y, seed):
    nn = MLPClassifier(hidden_layer_sizes=(128, 64), batch_size=2048,
                       learning_rate_init=3e-3, max_iter=200, early_stopping=True,
                       n_iter_no_change=10, random_state=seed)
    nn.fit(X.astype(np.float32), y)
    return nn


def se(pl, n):
    return float((pl * (1 - pl) / n) ** 0.5)


def confronto(rounds, p, modo, p_meas, shots, seed):
    det, obs = campiona(rounds, p, modo, p_meas, shots, seed)
    n_tr = int(shots * 0.75)
    m = build_matching(rounds, p, p_meas)
    pred = m.decode_batch(det[n_tr:])[:, 0].astype(np.uint8)
    y_te = obs[n_tr:]
    pL_m = float((pred != y_te).mean())

    nn = train_nn(det[:n_tr], obs[:n_tr], seed)
    prob = nn.predict_proba(det[n_tr:].astype(np.float32))[:, 1]
    pL_n = float(((prob >= 0.5) != y_te).mean())

    # ibrido residuale: la rete impara quando ribaltare il matching (come in Sez. 12.7)
    Xh = np.concatenate([det, np.zeros((len(det), 1), dtype=np.uint8)], axis=1)
    pred_tr = m.decode_batch(det[:n_tr])[:, 0].astype(np.uint8)
    Xh[:n_tr, -1] = pred_tr
    Xh[n_tr:, -1] = pred
    nnh = train_nn(Xh[:n_tr], (pred_tr != obs[:n_tr]).astype(np.uint8), seed)
    pe = nnh.predict_proba(Xh[n_tr:].astype(np.float32))[:, 1]
    pL_h = float(((pred ^ (pe >= 0.5)) != y_te).mean())

    n_te = len(y_te)
    return {'modo': modo, 'p': p, 'rounds': rounds, 'shots': shots,
            'base_rate': float(obs.mean()),
            'pL_mwpm': pL_m, 'pL_mwpm_se': se(pL_m, n_te),
            'pL_nn': pL_n, 'pL_nn_se': se(pL_n, n_te),
            'pL_ibrido': pL_h, 'pL_ibrido_se': se(pL_h, n_te),
            'guadagno_ibrido': pL_m / pL_h if pL_h > 0 else None,
            'auc_residuo': float(roc_auc_score((pred != y_te), pe))
                            if 0 < (pred != y_te).mean() < 1 else None,
            'n_test': int(n_te)}


def main():
    ap = argparse.ArgumentParser(description='M12 — errori coerenti vs Pauli')
    ap.add_argument('--shots', type=int, default=40000)
    ap.add_argument('--rounds', type=int, default=3)
    ap.add_argument('--p-meas', type=float, default=0.01)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--p-list', type=float, nargs='+', default=[0.01, 0.02, 0.04])
    args = ap.parse_args()

    print('=' * 76)
    print('M12 — il decoder appreso guadagna di piu\' sugli errori COERENTI?')
    print(f"    surface code d=3, memory Z, {args.rounds} cicli, "
          f"errore di lettura {args.p_meas}")
    print('=' * 76)
    print('  modo       p      banale   MWPM      rete      IBRIDO    ibrido/MWPM')
    print('  ' + '-' * 68)

    out = []
    for p in args.p_list:
        for modo in ('pauli', 'coerente'):
            r = confronto(args.rounds, p, modo, args.p_meas, args.shots, args.seed)
            g = r['guadagno_ibrido']
            gtxt = f"{g:.3f}x" if g else "n/d"
            print(f"  {modo:<10} {p:<6g} {r['base_rate']:.4f}   {r['pL_mwpm']:.5f}   "
                  f"{r['pL_nn']:.5f}   {r['pL_ibrido']:.5f}   {gtxt}", flush=True)
            out.append(r)

    print('\n' + '=' * 76)
    print('ESITO M12 — confronto del guadagno fra i due tipi di rumore')
    print('=' * 76)
    for p in args.p_list:
        gp = next((r['guadagno_ibrido'] for r in out
                   if r['p'] == p and r['modo'] == 'pauli'), None)
        gc = next((r['guadagno_ibrido'] for r in out
                   if r['p'] == p and r['modo'] == 'coerente'), None)
        if gp and gc:
            print(f"  p={p:<6g} guadagno su Pauli {gp:.3f}x | su coerente {gc:.3f}x "
                  f"| rapporto {gc/gp:.2f}")
    gp = np.mean([r['guadagno_ibrido'] for r in out
                  if r['modo'] == 'pauli' and r['guadagno_ibrido']])
    gc = np.mean([r['guadagno_ibrido'] for r in out
                  if r['modo'] == 'coerente' and r['guadagno_ibrido']])
    print(f"\n  guadagno medio  Pauli {gp:.3f}x   coerente {gc:.3f}x")
    if gc > gp * 1.05:
        flag = 'VERDE — la previsione del criterio e\' CONFERMATA: il guadagno e\' maggiore sui coerenti'
    elif gc < gp * 0.95:
        flag = 'ROSSO — previsione SMENTITA: il guadagno e\' minore sui coerenti'
    else:
        flag = 'GIALLO — nessuna differenza apprezzabile fra i due tipi di rumore'
    print(f'  FLAG: {flag}')

    fn = f"results_M12_coerenti_{datetime.now():%Y%m%d_%H%M%S}.json"
    json.dump({'milestone': 'M12_coerenti', 'timestamp': datetime.now().isoformat(),
               'rounds': args.rounds, 'p_meas': args.p_meas, 'seed': args.seed,
               'guadagno_medio_pauli': float(gp), 'guadagno_medio_coerente': float(gc),
               'flag': flag, 'punti': out}, open(fn, 'w'), indent=2)
    print(f'\nRisultati salvati in: {fn}')


if __name__ == '__main__':
    main()
