"""Costo di simulazione per iterazione di UC1, UC3 e UC4.

In presenza di un modello di rumore AerSimulator non puo' evolvere lo stato una volta
sola e ricampionarlo: ogni shot e' una traiettoria indipendente. Il costo di una
iterazione da 1024 shot e' quindi ~1024 volte quello di una traiettoria — ma NON si
misura dividendo il tempo di poche traiettorie per il loro numero.

ATTENZIONE, errore da non ripetere: Aer parallelizza le traiettorie sui core, quindi
il costo per shot cala nettamente al crescere del numero di shot. Su UC1 misurato:

     4 shot -> 32.6 ms/shot     256 shot ->  3.4 ms/shot
    64 shot ->  8.0 ms/shot    1024 shot ->  2.9 ms/shot

Una stima ricavata da 4 traiettorie sovrastima quindi il costo unitario di un fattore
~11. Questo script misura a piu' valori di shot e riporta la curva, cosi' che il costo
per iterazione sia estrapolato dal regime gia' ammortizzato e non da quello iniziale.

Va eseguito a macchina scarica: la contesa con altri processi gonfia i tempi.
"""
import time
import warnings

warnings.filterwarnings('ignore')

from qiskit import transpile
from qiskit_aer import AerSimulator

from shor_core import shor_circuit, build_noise_model

RUMORE = dict(eps_1q=1e-3, eps_2q=1e-2, t1_ns=100_000, t2_ns=80_000, p_ro=0.02)
PORTE_2Q = ('cx', 'swap', 'cp')
SHOT_ITERAZIONE = 1024

# (nome, N, a, n_count, shot su cui misurare) — scale ridotte per le istanze grandi
CASI = [
    ('UC1', 15, 7, 8, (4, 64, 256, 1024)),
    ('UC3', 21, 2, 10, (4, 16, 64)),
    ('UC4', 35, 6, 12, (4, 16, 64)),
]

for nome, N, a, n_count, scale in CASI:
    nm = build_noise_model(**RUMORE)
    sim = AerSimulator(noise_model=nm, method='statevector')
    t = transpile(shor_circuit(N, a, n_count), sim, optimization_level=2)
    ops = dict(t.count_ops())
    k_2q = sum(ops.get(g, 0) for g in PORTE_2Q)
    print(f'--- {nome}: {t.num_qubits} qubit, profondita {t.depth()}, '
          f'cx {ops.get("cx", 0)}, cp {ops.get("cp", 0)}, k_2q {k_2q}, '
          f'P_surv {(1 - RUMORE["eps_2q"]) ** k_2q:.3g}', flush=True)

    ultimo_ms = None
    for s in scale:
        t0 = time.time()
        sim.run(t, shots=s, seed_simulator=1).result()
        dt = time.time() - t0
        ultimo_ms = dt / s * 1000
        print(f'    {s:5d} shot -> {dt:9.2f} s totali  =  {ultimo_ms:10.2f} ms/shot',
              flush=True)

    # Estrapolazione al costo di una iterazione, dal punto piu' ammortizzato misurato.
    iter_s = ultimo_ms / 1000 * SHOT_ITERAZIONE
    print(f'    => iterazione da {SHOT_ITERAZIONE} shot: {iter_s:.1f} s '
          f'({iter_s / 3600:.2f} h)   [estrapolato da {scale[-1]} shot, '
          f'valore per eccesso se la curva non e\' ancora piatta]\n', flush=True)
