"""
pilot_calibration.py — Fase 0: trova i parametri di rumore ottimali per i 4 use case.

Step 2: tasso di successo per singola exec con rumore NISQ-realistico
Step 3: calibra NISQ-degradato per UC2
Step 4: verifica N=21 e N=35

Output: stampa una tabella riassuntiva e suggerisce i parametri definitivi per i 4 UC.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from shor_core import build_noise_model, run_method1, shor_circuit
from qiskit import transpile
from qiskit_aer import AerSimulator


N_PILOT = 30   # ripetizioni per ogni configurazione (bilanciamento velocità/affidabilità)
SHOTS   = 1024


def test_noise_config(N, a, n_count, noise_params, label, n_pilot=N_PILOT):
    """Esegui n_pilot run di M1 e restituisci statistiche."""
    nm  = build_noise_model(**noise_params)
    results = []
    for seed in range(n_pilot):
        r = run_method1(N, a, n_count, nm, shots=SHOTS, max_iter=1, seed=seed)
        results.append(r['success'])
    success_rate = sum(results) / n_pilot

    # Stima M̄₁ con max_iter abbondante
    iters = []
    for seed in range(n_pilot):
        r = run_method1(N, a, n_count, nm, shots=SHOTS, max_iter=200, seed=seed)
        if r['success']:
            iters.append(r['iterations'])
    m_bar = np.mean(iters) if iters else float('inf')

    print(f"  {label:40s}  success_rate={success_rate:.0%}  M̄₁={m_bar:.1f}  (n={n_pilot})")
    return success_rate, m_bar


# ──────────────────────────────────────────────────
# STEP 2 — N=15: testa vari livelli eps_2q per trovare il regime interessante
# ──────────────────────────────────────────────────
print("\n" + "="*70)
print("STEP 2 — N=15, a=7, n_count=8  (variazione eps_2q)")
print("Regime interessante: success_rate 10%-50%")
print("="*70)

BASE = {'eps_1q': 1e-3, 't1_ns': 100_000, 't2_ns': 80_000, 'p_ro': 0.02}

step2_results = {}
for eps_2q in [5e-3, 1e-2, 2e-2, 3e-2, 5e-2]:
    noise = {**BASE, 'eps_2q': eps_2q}
    label = f"eps_2q={eps_2q:.0e}"
    sr, mb = test_noise_config(15, 7, 8, noise, label)
    step2_results[eps_2q] = (sr, mb)

# Scegli il livello "realistico" (più vicino al 10-50% range, M̄₁ in decine)
print("\n→ Selezione eps_2q NISQ-realistico:")
realistic_eps = None
for eps_2q, (sr, mb) in step2_results.items():
    if 0.10 <= sr <= 0.55 and mb != float('inf'):
        if realistic_eps is None or abs(sr - 0.30) < abs(step2_results[realistic_eps][0] - 0.30):
            realistic_eps = eps_2q

if realistic_eps is None:
    # Fallback: prendi il primo sotto il 60%
    for eps_2q in sorted(step2_results):
        if step2_results[eps_2q][0] < 0.60:
            realistic_eps = eps_2q
            break

print(f"  eps_2q REALISTICO scelto: {realistic_eps:.0e}  (success_rate={step2_results[realistic_eps][0]:.0%}  M̄₁={step2_results[realistic_eps][1]:.1f})")

NOISE_REALISTIC = {**BASE, 'eps_2q': realistic_eps}

# ──────────────────────────────────────────────────
# STEP 3 — N=15: calibra NISQ-degradato (M̄₁_deg / M̄₁_real ≈ 3-10×)
# ──────────────────────────────────────────────────
print("\n" + "="*70)
print("STEP 3 — N=15: calibrazione NISQ-degradato per UC2")
print("Obiettivo: M̄₁_degradato / M̄₁_realistico ≈ 3-10×")
print("="*70)

m1_real = step2_results[realistic_eps][1]

step3_results = {}
for factor in [2, 5, 10]:
    noise_deg = {
        'eps_1q': 5e-3,
        'eps_2q': min(realistic_eps * factor, 0.25),
        't1_ns':  50_000,
        't2_ns':  30_000,
        'p_ro':   0.05
    }
    label = f"×{factor} ({noise_deg['eps_2q']:.0e})"
    sr, mb = test_noise_config(15, 7, 8, noise_deg, label)
    step3_results[factor] = (noise_deg, sr, mb)

print(f"\n  M̄₁ realistico = {m1_real:.1f}")
degraded_factor = None
for factor, (noise_deg, sr, mb) in step3_results.items():
    ratio = mb / m1_real if m1_real > 0 and mb != float('inf') else float('inf')
    print(f"  ×{factor}: M̄₁_deg={mb:.1f}  ρ_atteso={ratio:.1f}")
    if 2.0 <= ratio <= 15.0 and degraded_factor is None:
        degraded_factor = factor

if degraded_factor is None:
    degraded_factor = 5  # fallback
NOISE_DEGRADED = step3_results[degraded_factor][0]
print(f"\n→ NISQ-degradato scelto: ×{degraded_factor}")

# ──────────────────────────────────────────────────
# STEP 4 — Verifica N=21 e N=35
# ──────────────────────────────────────────────────
print("\n" + "="*70)
print("STEP 4 — Verifica N=21 e N=35")
print("="*70)

# N=21: n_count deve soddisfare 2^n_count >= N^2 => n_count=9 min, usiamo 10
# N=35: n_count=12 come da CLAUDE.md
for N_test, a_test, n_count_test in [(21, 2, 10), (35, 6, 12)]:
    try:
        qc = shor_circuit(N_test, a_test, n_count_test)
        sim = AerSimulator(method='statevector')
        qct = transpile(qc, sim, optimization_level=3)
        depth = qct.depth()

        # Test ideale: deve avere picchi coerenti
        counts = sim.run(qct, shots=512).result().get_counts()
        top3 = sorted(counts.items(), key=lambda x: -x[1])[:3]
        top3_str = ', '.join(f"{int(b,2)}({c})" for b,c in top3)

        # Test con rumore
        sr, mb = test_noise_config(N_test, a_test, n_count_test, NOISE_REALISTIC,
                                   f"N={N_test} a={a_test} n={n_count_test}", n_pilot=15)

        print(f"  N={N_test} a={a_test} n_count={n_count_test}: depth={depth}  top3_ideale=[{top3_str}]")
        print(f"  → success_rate={sr:.0%}  M̄₁={mb:.1f}")

        if depth > 1000:
            print(f"  ⚠ ATTENZIONE: depth={depth} > 1000. Considera di ridurre n_count.")

    except Exception as e:
        print(f"  N={N_test} ERRORE: {e}")

# ──────────────────────────────────────────────────
# RIEPILOGO FINALE
# ──────────────────────────────────────────────────
print("\n" + "="*70)
print("RIEPILOGO — PARAMETRI DEFINITIVI (da aggiornare in CLAUDE.md)")
print("="*70)
print(f"""
NOISE_REALISTIC = {{
    'eps_1q': {NOISE_REALISTIC['eps_1q']},
    'eps_2q': {NOISE_REALISTIC['eps_2q']},
    't1_ns':  {NOISE_REALISTIC['t1_ns']},
    't2_ns':  {NOISE_REALISTIC['t2_ns']},
    'p_ro':   {NOISE_REALISTIC['p_ro']}
}}

NOISE_DEGRADED = {{
    'eps_1q': {NOISE_DEGRADED['eps_1q']},
    'eps_2q': {NOISE_DEGRADED['eps_2q']},
    't1_ns':  {NOISE_DEGRADED['t1_ns']},
    't2_ns':  {NOISE_DEGRADED['t2_ns']},
    'p_ro':   {NOISE_DEGRADED['p_ro']}
}}
""")
print("  UC1: N=15, a=7, n_count=8,  NOISE_REALISTIC")
print("  UC2: N=15, a=7, n_count=8,  NOISE_DEGRADED")
print("  UC3: N=21, a=2, n_count=10, NOISE_REALISTIC")
print("  UC4: N=35, a=6, n_count=12, NOISE_REALISTIC")
