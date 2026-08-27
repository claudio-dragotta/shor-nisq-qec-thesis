"""
run_top4_baseline.py — Testa la variante TOP-4 senza classificatore (M_TOP4).

Scopo: isolare il contributo del classificatore ML da quello della ricerca
multi-candidato. Confronta tre varianti sullo stesso circuito, stessi seed:
  M1      = TOP-1, nessun filtro
  M_TOP4  = TOP-4, nessun filtro  ← NEW
  M2      = CLF + TOP-4

Se M_TOP4 ≈ M2 → il miglioramento è tutto della ricerca TOP-4, il classificatore
               non aggiunge valore.
Se M_TOP4 > M2 → il classificatore contribuisce filtrando iterazioni inutili.

Eseguire da WSL:
  source ~/quantum-env/bin/activate
  cd ~/path/to/experiments
  python run_top4_baseline.py
"""

import os
from pathlib import Path

import joblib
import numpy as np
from scipy.stats import wilcoxon
from shor_core import (
    build_noise_model,
    compile_shor_circuit,
    extract_factors,
    experiment_manifest,
    rank_measurements,
)
from qiskit_aer import AerSimulator

NOISE_REALISTIC     = dict(eps_1q=1e-3,  eps_2q=1e-2,  t1_ns=100_000, t2_ns=80_000,  p_ro=0.02)
NOISE_DEGRADED      = dict(eps_1q=5e-3,  eps_2q=5e-2,  t1_ns=50_000,  t2_ns=30_000,  p_ro=0.05)
NOISE_NEARFUTURE_HARD = dict(eps_1q=1e-4, eps_2q=1e-3,  t1_ns=500_000, t2_ns=400_000, p_ro=0.005)
NOISE_NEARFUTURE_EASY = dict(eps_1q=5e-5, eps_2q=5e-4,  t1_ns=800_000, t2_ns=600_000, p_ro=0.002)

K        = 30
SHOTS    = 1024
MAX_ITER = 50


def paired_wilcoxon(a, b, alternative='greater'):
    """Wilcoxon appaiato con gestione esplicita del caso tutti-pareggi."""
    a, b = np.asarray(a), np.asarray(b)
    if np.array_equal(a, b):
        return 0.0, 1.0
    result = wilcoxon(
        a, b, alternative=alternative, zero_method='pratt', method='auto'
    )
    return float(result.statistic), float(result.pvalue)


def paired_greater(a, b):
    return paired_wilcoxon(a, b, alternative='greater')


def run_method_top4(N, a, n_count, noise_model, shots=1024, max_iter=50, seed=42):
    """TOP-4 senza classificatore: tenta i 4 candidati più frequenti ogni iterazione."""
    sim = AerSimulator(noise_model=noise_model, method='statevector')
    transpiled = compile_shor_circuit(N, a, n_count)
    for iteration in range(1, max_iter + 1):
        simulation_seed = seed * 1_000_000 + iteration * 10_000
        counts = sim.run(transpiled, shots=shots,
                         seed_simulator=simulation_seed).result().get_counts()
        sorted_meas = rank_measurements(counts, simulation_seed)
        for meas_str, _ in sorted_meas[:4]:
            p, q = extract_factors(int(meas_str, 2), n_count, N, a)
            if p is not None:
                return {'iterations': iteration, 'success': True, 'factors': (p, q)}
    return {'iterations': max_iter, 'success': False, 'factors': (None, None)}


def _encoded_iteration(result, max_iter):
    """Mantiene distinguibile un successo a max_iter da un fallimento."""
    return result['iterations'] if result['success'] else max_iter + 1


def _load_compatible_classifier(model_path, uc_name, N, a, n_count):
    payload = joblib.load(model_path)
    current = experiment_manifest(N, a, n_count)
    model_manifest = payload.get('manifest', {})
    required = (
        'circuit_sha256', 'circuit_revision', 'noise_model_revision',
        'postprocess_revision',
    )
    if (payload.get('schema_version') != '2.0'
            or payload.get('use_case') != uc_name
            or payload.get('label_top_k') != 1
            or any(
        model_manifest.get(key) != current[key] for key in required
    )):
        raise ValueError(
            f'Classificatore incompatibile o storico: {model_path}. '
            'Rigenerarlo con train_classifier.py v2.'
        )
    return payload['clf']


def run_uc(uc_name, N, a, n_count, noise_params, with_m2=True,
           *, k=K, shots=SHOTS, max_iter=MAX_ITER, model_dir=None):
    nm  = build_noise_model(**noise_params)

    clf = None
    if with_m2:
        root = Path(model_dir or os.environ.get('SHOR_MODEL_DIR', '.'))
        model_path = root / f'clf_{uc_name}.joblib'
        try:
            clf = _load_compatible_classifier(
                model_path, uc_name, N, a, n_count
            )
        except FileNotFoundError:
            print(f'  Nessun classificatore in {model_path} — solo M1 e M_TOP4')
            with_m2 = False

    # Le tre strategie vedono lo stesso istogramma per ciascuna coppia
    # (replica, iterazione). Oltre a rendere l'appaiamento causale esplicito,
    # evita di simulare tre volte gli stessi shot.
    sim = AerSimulator(noise_model=nm, method='statevector')
    transpiled = compile_shor_circuit(N, a, n_count)
    m1, mt4, m2 = [], [], []
    for rep in range(k):
        print(f'  {uc_name} rep {rep+1}/{k}', end='\r', flush=True)
        found_m1 = found_top4 = found_m2 = None
        for iteration in range(1, max_iter + 1):
            simulation_seed = rep * 1_000_000 + iteration * 10_000
            counts = sim.run(
                transpiled, shots=shots, seed_simulator=simulation_seed
            ).result().get_counts()
            ranked = rank_measurements(counts, simulation_seed)
            valid = [
                extract_factors(int(bitstring, 2), n_count, N, a)[0]
                is not None
                for bitstring, _ in ranked[:4]
            ]
            if found_m1 is None and valid[0]:
                found_m1 = iteration
            if found_top4 is None and any(valid):
                found_top4 = iteration
            if with_m2 and found_m2 is None:
                feature = np.zeros(2 ** n_count)
                for bitstring, count in counts.items():
                    feature[int(bitstring, 2)] = count / shots
                if clf.predict([feature])[0] == 1 and any(valid):
                    found_m2 = iteration
            if (found_m1 is not None and found_top4 is not None
                    and (not with_m2 or found_m2 is not None)):
                break

        m1.append(found_m1 if found_m1 is not None else max_iter + 1)
        mt4.append(found_top4 if found_top4 is not None else max_iter + 1)
        if with_m2:
            m2.append(found_m2 if found_m2 is not None else max_iter + 1)
    print()
    return np.array(m1), np.array(mt4), (np.array(m2) if m2 else None)


def report(uc_name, m1, mt4, m2=None, *, k=K, max_iter=MAX_ITER):
    print(f'\n{"="*60}')
    print(f'  {uc_name}')
    print(f'{"="*60}')

    variants = [('M1  (TOP-1)    ', m1), ('M_TOP4 (TOP-4) ', mt4)]
    if m2 is not None:
        variants.append(('M2  (CLF+TOP-4)', m2))

    for label, arr in variants:
        ok = arr[arr <= max_iter]
        med = np.median(ok) if len(ok) > 0 else float('nan')
        print(f'  {label}  n_succ={len(ok)}/{k}  M̄={ok.mean() if len(ok) else float("nan"):.2f}'
              f'  σ={ok.std() if len(ok) else float("nan"):.2f}  med={med:.1f}')

    # Le repliche condividono il seed: il test deve essere appaiato.
    u1, p1 = paired_greater(m1, mt4)
    print(f'\n  Wilcoxon appaiato M1 > M_TOP4 : W={u1:.0f}  p={p1:.4f}',
          '→ sign.' if p1 < 0.05 else '→ n.s.')

    if m2 is not None:
        u2, p2 = paired_wilcoxon(mt4, m2, alternative='two-sided')
        u3, p3 = paired_greater(m1, m2)
        print(f'  Wilcoxon appaiato M_TOP4 vs M2: W={u2:.0f}  p={p2:.4f}',
              '→ sign.' if p2 < 0.05 else '→ n.s.')
        print(f'  Wilcoxon appaiato M1 > M2     : W={u3:.0f}  p={p3:.4f}',
              '→ sign.' if p3 < 0.05 else '→ n.s.')

    # Fattori di riduzione
    m1_ok  = m1[m1   <= max_iter]
    mt4_ok = mt4[mt4 <= max_iter]
    rho_top4 = m1_ok.mean() / mt4_ok.mean() if len(mt4_ok) and len(m1_ok) else float('nan')

    print(f'\n  rho(M1/M_TOP4) = {rho_top4:.3f}')
    if m2 is not None:
        m2_ok = m2[m2 <= max_iter]
        rho_m2 = m1_ok.mean() / m2_ok.mean() if len(m2_ok) and len(m1_ok) else float('nan')
        print(f'  rho(M1/M2)     = {rho_m2:.3f}')

    # Valori pronti per LaTeX
    mt4_psucc = 100 * len(mt4_ok) / k
    mt4_mean  = mt4_ok.mean() if len(mt4_ok) else float('nan')
    mt4_std   = mt4_ok.std()  if len(mt4_ok) else float('nan')
    mt4_med   = np.median(mt4_ok) if len(mt4_ok) else float('nan')
    print(f'\n  LaTeX row M_TOP4:')
    print(f'  M_TOP4 & {mt4_psucc:.1f}\\% & {mt4_mean:.2f} & {mt4_std:.2f} & {mt4_med:.0f} & {rho_top4:.3f} \\\\')
    print(f'  W(M1>M_TOP4)={u1:.0f}  p={p1:.4f}')


if __name__ == '__main__':
    raise SystemExit(
        'Questo modulo fornisce helper alla campagna v2. '
        'Eseguire rerun_baseline_corretto.py; N=21/35 non viene simulato con rumore.'
    )
