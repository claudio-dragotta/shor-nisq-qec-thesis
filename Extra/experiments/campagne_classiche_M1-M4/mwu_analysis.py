"""
mwu_analysis.py — Calcola Mann-Whitney U test per M1 vs M2 su UC1 e UC2.
Usa gli stessi seed deterministici di run_experiments.py → risultati identici.
Stampa i valori pronti da copiare nel LaTeX.
"""
import joblib
import numpy as np
from scipy.stats import mannwhitneyu, wilcoxon
from shor_core import build_noise_model, run_method1, run_method2

NOISE_REALISTIC = {'eps_1q': 1e-3, 'eps_2q': 1e-2,
                   't1_ns': 100_000, 't2_ns': 80_000, 'p_ro': 0.02}
NOISE_DEGRADED  = {'eps_1q': 5e-3, 'eps_2q': 5e-2,
                   't1_ns': 50_000,  't2_ns': 30_000,  'p_ro': 0.05}

K         = 30
SHOTS     = 1024
MAX_ITER  = 50

def collect(uc_name, N, a, n_count, noise_params):
    nm  = build_noise_model(**noise_params)
    clf_data = joblib.load(f"clf_{uc_name}.joblib")
    clf = clf_data['clf']

    m1_iters, m2_iters = [], []
    for rep in range(K):
        print(f"  {uc_name} rep {rep+1}/{K}", end='\r', flush=True)
        r1 = run_method1(N, a, n_count, nm, shots=SHOTS, max_iter=MAX_ITER, seed=rep)
        r2 = run_method2(N, a, n_count, nm, clf, shots=SHOTS, max_iter=MAX_ITER, seed=rep)
        # Fallimenti → MAX_ITER (censored)
        m1_iters.append(r1['iterations'])
        m2_iters.append(r2['iterations'])
    print()
    return np.array(m1_iters), np.array(m2_iters)

def report(uc_name, m1, m2):
    print(f"\n{'='*55}")
    print(f"  {uc_name}")
    print(f"{'='*55}")

    # Statistiche descrittive (solo successi)
    m1_ok = m1[m1 < MAX_ITER]
    m2_ok = m2[m2 < MAX_ITER]
    print(f"  M1: n_succ={len(m1_ok)}/{K}  M̄={m1_ok.mean():.2f}  σ={m1_ok.std():.2f}  med={np.median(m1_ok):.1f}")
    print(f"  M2: n_succ={len(m2_ok)}/{K}  M̄={m2_ok.mean():.2f}  σ={m2_ok.std():.2f}  med={np.median(m2_ok):.1f}")

    # Mann-Whitney U (su tutti i K valori, inclusi censored a MAX_ITER)
    stat, p_mwu = mannwhitneyu(m1, m2, alternative='greater')
    print(f"\n  Mann-Whitney U (M1 > M2): U={stat:.1f}  p={p_mwu:.4f}",
          "→ sign." if p_mwu < 0.05 else "→ n.s.")

    # Wilcoxon signed-rank (su coppie: stesso seed, stessa run)
    try:
        stat_w, p_w = wilcoxon(m1, m2, alternative='greater')
        print(f"  Wilcoxon signed-rank:     W={stat_w:.1f}  p={p_w:.4f}",
              "→ sign." if p_w < 0.05 else "→ n.s.")
    except Exception as e:
        print(f"  Wilcoxon: {e}")

    print(f"\n  → LaTeX (Mann-Whitney): U={stat:.0f}, p={p_mwu:.3f}")

if __name__ == '__main__':
    print("Raccolta dati UC1 (N=15, NISQ-realistico)...")
    m1_uc1, m2_uc1 = collect('UC1', 15, 7, 8, NOISE_REALISTIC)

    print("Raccolta dati UC2 (N=15, NISQ-degradato)...")
    m1_uc2, m2_uc2 = collect('UC2', 15, 7, 8, NOISE_DEGRADED)

    report('UC1 — NISQ-realistico', m1_uc1, m2_uc1)
    report('UC2 — NISQ-degradato',  m1_uc2, m2_uc2)

    print("\nCopia i valori U e p nel LaTeX (RisultatiMetodo2.tex).")
