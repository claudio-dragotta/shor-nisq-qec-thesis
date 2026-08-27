"""
generate_figures.py — Genera le figure per la tesi (Cap. 10-11).

Figure prodotte (salvate in ../file_latex/figure/):
  fig_istogrammi_qpe.pdf   — Istogramma QPE con segnale vs istogramma piatto (UC1)
  fig_roc_curve.pdf        — Curve ROC dei classificatori (UC1: RF, UC2: SVM)
  fig_iterazioni_m1_m2.pdf — Box plot iterazioni M1 vs M2 su UC1

Eseguire da WSL con quantum-env attivato:
  source ~/quantum-env/bin/activate
  cd ~/path/to/experiments
  python generate_figures.py
"""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from sklearn.metrics import roc_curve, auc

from shor_core import (
    build_noise_model,
    compile_shor_circuit,
    experiment_manifest,
)
from qiskit_aer import AerSimulator

# Percorso relativo alla posizione di questo file, non alla cwd: il riordino del
# 2026-07-09 ha spostato lo script in Extra/experiments/campagne_classiche_M1-M4/,
# e il vecchio '../file_latex/figure' non punta piu' alla cartella delle figure.
OUT_DIR = Path(__file__).resolve().parents[3] / 'file_latex' / 'figure'
MODEL_DIR = Path('.')
BASELINE_JSON = None
FIGSIZE_WIDE  = (10, 4)
FIGSIZE_SQUARE = (6, 5)
FIGSIZE_BOX   = (6, 5)

NOISE_REALISTIC = dict(eps_1q=1e-3, eps_2q=1e-2, t1_ns=100_000, t2_ns=80_000, p_ro=0.02)
NOISE_DEGRADED  = dict(eps_1q=5e-3, eps_2q=5e-2, t1_ns=50_000,  t2_ns=30_000,  p_ro=0.05)


# ──────────────────────────────────────────────
# Figura 1: Istogrammi QPE comparativi (UC1)
# ──────────────────────────────────────────────

def fig_istogrammi_qpe():
    print('Generazione fig_istogrammi_qpe.pdf ...')
    nm = build_noise_model(**NOISE_REALISTIC)
    sim = AerSimulator(noise_model=nm, method='statevector')
    tc  = compile_shor_circuit(15, 7, 8)

    # Selezione dichiarata e riproducibile: tra le prime 30 repliche della campagna
    # scegli i campioni con minima/massima massa sui quattro picchi teorici.
    candidates = []
    theoretical_peaks = {0, 64, 128, 192}
    for rep in range(30):
        simulator_seed = rep * 1_000_000 + 10_000
        counts = sim.run(
            tc, shots=1024, seed_simulator=simulator_seed
        ).result().get_counts()
        peak_mass = sum(
            value for bits, value in counts.items()
            if int(bits, 2) in theoretical_peaks
        ) / 1024
        candidates.append((peak_mass, rep, simulator_seed, counts))
    weakest = min(candidates, key=lambda item: (item[0], item[1]))
    strongest = max(candidates, key=lambda item: (item[0], -item[1]))
    counts_good = strongest[3]
    counts_flat = weakest[3]

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_WIDE)

    for ax, counts, title, color in zip(
        axes,
        [counts_good, counts_flat],
        ['Campione più concentrato sui picchi', 'Campione meno concentrato sui picchi'],
        ['steelblue', 'tomato']
    ):
        x = np.arange(256)
        y = np.zeros(256)
        for k, v in counts.items():
            y[int(k, 2)] = v / 1024

        ax.bar(x, y, color=color, alpha=0.75, width=1.0)
        # Evidenzia i picchi teorici: 64, 128, 192
        for peak in [64, 128, 192]:
            ax.axvline(peak, color='black', linestyle='--', linewidth=1.0, alpha=0.7)
        ax.set_title(title, fontsize=11)
        ax.set_xlabel('Misura QPE (valore decimale)', fontsize=10)
        ax.set_ylabel('Frequenza relativa', fontsize=10)
        ax.set_xlim(0, 255)
        ax.set_xticks([0, 64, 128, 192, 255])

    axes[0].annotate('64', xy=(64, axes[0].get_ylim()[1]*0.95), ha='center', fontsize=9)
    axes[0].annotate('128', xy=(128, axes[0].get_ylim()[1]*0.95), ha='center', fontsize=9)
    axes[0].annotate('192', xy=(192, axes[0].get_ylim()[1]*0.95), ha='center', fontsize=9)

    fig.suptitle(
        'Istogrammi QPE — UC1 ($N=15$, preset uniforme di riferimento)',
        fontsize=12,
    )
    plt.tight_layout()
    path = OUT_DIR / 'fig_istogrammi_qpe.pdf'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    provenance = {
        'schema_version': '2.0',
        'artifact_type': 'qpe-histogram-selection-provenance',
        'manifest': experiment_manifest(),
        'noise': dict(NOISE_REALISTIC),
        'selection_rule': 'max/min theoretical-peak mass over campaign reps 0..29',
        'candidate_replicates': list(range(30)),
        'shots': 1024,
        'strongest': {
            'rep': strongest[1], 'seed_simulator': strongest[2],
            'peak_mass': strongest[0],
        },
        'weakest': {
            'rep': weakest[1], 'seed_simulator': weakest[2],
            'peak_mass': weakest[0],
        },
    }
    (OUT_DIR / 'fig_istogrammi_qpe_provenance.json').write_text(
        json.dumps(provenance, indent=2), encoding='utf-8'
    )
    print(f'  → {path}')


# ──────────────────────────────────────────────
# Figura 2: Curve ROC
# ──────────────────────────────────────────────

def fig_roc_curve():
    print('Generazione fig_roc_curve.pdf ...')

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_WIDE)
    current_manifest = experiment_manifest()

    configs = [
        ('UC1', 'clf_UC1.joblib', NOISE_REALISTIC, 'steelblue'),
        ('UC2', 'clf_UC2.joblib', NOISE_DEGRADED,  'darkorange'),
    ]

    for ax, (uc_name, clf_path, noise_params, color) in zip(axes, configs):
        data = joblib.load(MODEL_DIR / clf_path)
        model_manifest = data.get('manifest', {})
        required = (
            'circuit_sha256', 'circuit_revision', 'noise_model_revision',
            'postprocess_revision',
        )
        if (data.get('schema_version') != '2.0'
                or data.get('label_top_k') != 1
                or data.get('use_case') != uc_name
                or any(model_manifest.get(key) != current_manifest.get(key)
                       for key in required)):
            raise ValueError(f'Modello storico o incompatibile: {clf_path}')
        clf    = data['clf']
        model_name = data['name']
        X_test = data['X_test']
        y_test = data['y_test']

        if hasattr(clf, 'predict_proba'):
            y_score = clf.predict_proba(X_test)[:, 1]
        else:
            y_score = clf.decision_function(X_test)

        fpr, tpr, _ = roc_curve(y_test, y_score)
        roc_auc = auc(fpr, tpr)

        ax.plot(fpr, tpr, color=color, lw=2,
                label=f'{model_name} (AUC = {roc_auc:.3f})')
        ax.plot([0, 1], [0, 1], 'k--', lw=1, alpha=0.5)
        ax.set_xlim([0.0, 1.0])
        ax.set_ylim([0.0, 1.05])
        ax.set_xlabel('Tasso falsi positivi (FPR)', fontsize=10)
        ax.set_ylabel('Tasso veri positivi (TPR)', fontsize=10)
        ax.set_title(f'Curva ROC — {uc_name}', fontsize=11)
        ax.legend(loc='lower right', fontsize=9)

    fig.suptitle('Curve ROC dei classificatori selezionati', fontsize=12)
    plt.tight_layout()
    path = OUT_DIR / 'fig_roc_curve.pdf'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f'  → {path}')


# ──────────────────────────────────────────────
# Figura 3: Distribuzione iterazioni M1 vs M2 (UC1)
# ──────────────────────────────────────────────

def fig_iterazioni_m1_m2():
    print(f'Caricamento iterazioni v2 da {BASELINE_JSON} ...')
    payload = json.loads(Path(BASELINE_JSON).read_text(encoding='utf-8'))
    if (payload.get('schema_version') != '2.0'
            or payload.get('analysis_revision')
            != 'baseline-shared-hist-ties-holm-v3'):
        raise ValueError('baseline-json non appartiene al contratto baseline v3')
    uc1 = next(item for item in payload['use_case'] if item['use_case'] == 'UC1')
    max_iter = int(uc1['max_iter'])
    m1_iters = uc1['_iterazioni']['M1']
    mt4_iters = uc1['_iterazioni']['M_TOP4']
    m2_iters = uc1['_iterazioni']['M2']
    if m2_iters is None:
        raise ValueError('La baseline UC1 non contiene M2: modello TOP-1 mancante.')

    m1  = np.array(m1_iters)
    mt4 = np.array(mt4_iters)
    m2  = np.array(m2_iters)

    fig, ax = plt.subplots(figsize=(7, 5))

    bp = ax.boxplot(
        [m1, mt4, m2],
        tick_labels=['M1\n(TOP-1)', '$M_{\\mathrm{TOP4}}$\n(no clf)', 'M2\n(CLF+TOP-4)'],
        patch_artist=True,
        medianprops=dict(color='black', linewidth=2),
        flierprops=dict(marker='o', markerfacecolor='gray', markersize=5, alpha=0.5),
        widths=0.5,
    )
    bp['boxes'][0].set_facecolor('#aec6e8')
    bp['boxes'][1].set_facecolor('#a8d8a8')
    bp['boxes'][2].set_facecolor('#ffb347')

    y_max = max(m1.max(), mt4.max(), m2.max())
    for i, arr in enumerate([m1, mt4, m2], start=1):
        successful = arr[arr <= max_iter]
        mean_success = successful.mean() if len(successful) else float('nan')
        censored = len(arr) - len(successful)
        ax.text(i, arr.mean() + 0.06 * y_max,
                f'$\\bar{{M}}_{{succ}}={mean_success:.2f}$\n'
                f'cens.={censored}',
                ha='center', fontsize=9, color='black')

    # p-value corretti per i tre confronti della famiglia baseline.
    p1 = uc1['wilcoxon_M1_gt_TOP4'].get(
        'p_holm', uc1['wilcoxon_M1_gt_TOP4']['p']
    )
    p2 = uc1['wilcoxon_M2_vs_TOP4'].get(
        'p_holm', uc1['wilcoxon_M2_vs_TOP4']['p']
    )
    ax.text(0.98, 0.97,
            f'M1$>$$M_{{\\mathrm{{TOP4}}}}$: $p_{{\\rm Holm}}={p1:.4f}$\n'
            f'Ablazione bilaterale: $p_{{\\rm Holm}}={p2:.3f}$',
            transform=ax.transAxes, ha='right', va='top', fontsize=8,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

    ax.set_ylabel('Iterazioni per ottenere i fattori corretti', fontsize=10)
    ax.set_title('UC1 — Analisi di ablazione: M1, $M_{\\mathrm{TOP4}}$, M2\n'
                 '($N=15$, preset uniforme di riferimento, $K=30$, '
                 '$M_{\\mathrm{max}}=50$)', fontsize=11)
    # Scala adattiva: con il seeding corretto le iterazioni restano sotto la decina,
    # e un asse fisso a M_max = 50 schiaccerebbe i tre box sulla linea di base.
    ax.set_ylim(0, y_max * 1.25)
    ax.axhline(1, color='gray', linestyle=':', linewidth=1, alpha=0.6)
    ax.text(3.38, 1.05, 'ottimo', fontsize=8, color='gray')

    plt.tight_layout()
    path = OUT_DIR / 'fig_iterazioni_m1_m2.pdf'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f'  → {path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--model-dir', type=Path, required=True)
    parser.add_argument('--baseline-json', type=Path, required=True)
    args = parser.parse_args()
    OUT_DIR = args.output_dir
    MODEL_DIR = args.model_dir
    BASELINE_JSON = args.baseline_json
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Figura 1: selezione riproducibile su 30 run x 1024 shot.
    fig_istogrammi_qpe()

    # Figura 2: usa solo i .joblib già addestrati
    fig_roc_curve()

    # Figura 3: usa esclusivamente il JSON baseline v2, senza rilanciare la campagna.
    fig_iterazioni_m1_m2()

    print('\nTutte le figure generate.')
