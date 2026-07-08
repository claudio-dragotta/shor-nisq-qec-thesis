"""Estrae tutte le righe LaTeX dai JSON degli sweep e le stampa raggruppate per tabella."""
import json
import numpy as np
from scipy.stats import mannwhitneyu

M1_UC1_ITERS = [1]*23 + [50]*7
M1_UC1_MBAR  = 6.43

FILES = {
    'k':     'results_parameter_analysis_20260522_193226.json',
    'eps':   'results_parameter_analysis_20260522_200927.json',
    'shots': 'results_parameter_analysis_20260522_203643.json',
    'joint': 'results_parameter_analysis_20260522_204121.json',
    't1t2':  'results_parameter_analysis_20260522_204254.json',
    'eps1q': 'results_parameter_analysis_20260522_204440.json',
    'pro':   'results_parameter_analysis_20260522_204625.json',
}


def mw(topk_iters, m1_iters=None):
    ref = m1_iters if m1_iters is not None else M1_UC1_ITERS
    _, p = mannwhitneyu(ref, topk_iters, alternative='greater')
    return float(p)

def rho(m_bar_topk, m_bar_m1=M1_UC1_MBAR):
    if m_bar_topk and m_bar_topk > 0:
        return round(m_bar_m1 / m_bar_topk, 3)
    return None

def fmt_p(p):
    if p < 0.001:
        return r'${<}0.001$'
    return f'${p:.3f}$'

def sig(p):
    return r'\textbf{sign.}' if p < 0.05 else 'n.s.'


# ── SWEEP K ──────────────────────────────────────────────────────────────────
with open(FILES['k']) as f:
    dk = json.load(f)['sweep_k']

print('% ============================================================')
print('% tabella sweep_k  (K & success_rate & M_bar & std & rho & p)')
print('% ============================================================')
for k_str, s in dk.items():
    p     = mw(s['all_iters'])
    r     = rho(s['M_bar'])
    mbar  = f"{s['M_bar']:.2f}" if s['M_bar'] else 'N/A'
    std   = f"{s['std']:.2f}"   if s['std']   else '---'
    psucc = f"{s['success_rate']*100:.0f}\\%"
    rval  = f"{r:.3f}"          if r           else '---'
    print(f"        {k_str} & {psucc} & {mbar} & {std} & {rval} & {fmt_p(p)} \\\\")
print()


# ── SWEEP EPS2Q ───────────────────────────────────────────────────────────────
with open(FILES['eps']) as f:
    de = json.load(f)['sweep_eps2q']

print('% ============================================================')
print('% tabella sweep_eps  (eps & P_surv & M1 & TOP4 & rho & p & sr)')
print('% ============================================================')
for eps_str, res in de.items():
    s1   = res['m1'];  stk = res['topk']
    p    = mw(stk['all_iters'], s1['all_iters'])
    r    = rho(stk['M_bar'], s1['M_bar']) if s1['M_bar'] else None
    m1s  = f"{s1['M_bar']:.2f}"  if s1['M_bar']  else 'N/A'
    tks  = f"{stk['M_bar']:.2f}" if stk['M_bar'] else 'N/A'
    rval = f"{r:.3f}"            if r             else '---'
    psucc= f"{stk['success_rate']*100:.0f}\\%"
    psrv = res['p_surv']
    print(f"        {eps_str} & ${psrv:.2e}$ & {m1s} & {tks} & {rval} & {fmt_p(p)} & {psucc} \\\\")
print()


# ── SWEEP SHOTS ───────────────────────────────────────────────────────────────
with open(FILES['shots']) as f:
    ds = json.load(f)['sweep_shots']

print('% ============================================================')
print('% tabella sweep_shots  (shots & sr & M_bar & std & rho)')
print('% ============================================================')
for sh_str, s in ds.items():
    p     = mw(s['all_iters'])
    r     = rho(s['M_bar'])
    mbar  = f"{s['M_bar']:.2f}" if s['M_bar'] else 'N/A'
    std   = f"{s['std']:.2f}"   if s['std']   else '---'
    psucc = f"{s['success_rate']*100:.0f}\\%"
    rval  = f"{r:.3f}"          if r           else '---'
    print(f"        {sh_str} & {psucc} & {mbar} & {std} & {rval} \\\\")
print()


# ── SWEEP JOINT ───────────────────────────────────────────────────────────────
with open(FILES['joint']) as f:
    dj = json.load(f)['sweep_joint']

print('% ============================================================')
print('% tabella sweep_joint  (K x eps_2q, celle = M_bar, grassetto se <=1.5)')
print('% ============================================================')
eps_sorted = sorted(next(iter(dj.values())).keys(), key=float)
header = ' & '.join([f'$\\varepsilon_{{2q}}={float(e):.0e}$' for e in eps_sorted])
print(f"        $K$ & {header} \\\\")
print("        \\midrule")
for k_str, eps_dict in dj.items():
    row = []
    for e in eps_sorted:
        s = eps_dict[e]
        if s and s.get('M_bar') is not None:
            val = f"{s['M_bar']:.2f}"
            if s['M_bar'] <= 1.5:
                val = f'\\textbf{{{val}}}'
        else:
            val = 'N/A'
        row.append(val)
    print(f"        {k_str} & " + ' & '.join(row) + ' \\\\')
print()


# ── SWEEP T1/T2 ───────────────────────────────────────────────────────────────
with open(FILES['t1t2']) as f:
    dt = json.load(f)['sweep_t1t2']

print('% ============================================================')
print('% tabella sweep_t1t2  (T1 [us] & T2 [us] & sr & M_bar & std & rho)')
print('% ============================================================')
for t1_str, s in dt.items():
    t1    = int(t1_str);  t2 = int(t1 * 0.8)
    p     = mw(s['all_iters'])
    r     = rho(s['M_bar'])
    mbar  = f"{s['M_bar']:.2f}" if s['M_bar'] else 'N/A'
    std   = f"{s['std']:.2f}"   if s['std']   else '---'
    psucc = f"{s['success_rate']*100:.0f}\\%"
    rval  = f"{r:.3f}"          if r           else '---'
    print(f"        {t1//1000} & {t2//1000} & {psucc} & {mbar} & {std} & {rval} \\\\")
print()


# ── SWEEP EPS1Q ───────────────────────────────────────────────────────────────
with open(FILES['eps1q']) as f:
    de1 = json.load(f)['sweep_eps1q']

print('% ============================================================')
print('% tabella sweep_eps1q  (eps_1q & sr & M_bar & std & rho)')
print('% ============================================================')
for e_str, s in de1.items():
    p     = mw(s['all_iters'])
    r     = rho(s['M_bar'])
    mbar  = f"{s['M_bar']:.2f}" if s['M_bar'] else 'N/A'
    std   = f"{s['std']:.2f}"   if s['std']   else '---'
    psucc = f"{s['success_rate']*100:.0f}\\%"
    rval  = f"{r:.3f}"          if r           else '---'
    print(f"        {e_str} & {psucc} & {mbar} & {std} & {rval} \\\\")
print()


# ── SWEEP P_RO ────────────────────────────────────────────────────────────────
with open(FILES['pro']) as f:
    dp = json.load(f)['sweep_pro']

print('% ============================================================')
print('% tabella sweep_pro  (p_ro & sr & M_bar & std & rho)')
print('% ============================================================')
for p_str, s in dp.items():
    p_ro  = float(p_str)
    p_val = mw(s['all_iters'])
    r     = rho(s['M_bar'])
    mbar  = f"{s['M_bar']:.2f}" if s['M_bar'] else 'N/A'
    std   = f"{s['std']:.2f}"   if s['std']   else '---'
    psucc = f"{s['success_rate']*100:.0f}\\%"
    rval  = f"{r:.3f}"          if r           else '---'
    print(f"        {p_ro*100:.0f}\\% & {psucc} & {mbar} & {std} & {rval} \\\\")
