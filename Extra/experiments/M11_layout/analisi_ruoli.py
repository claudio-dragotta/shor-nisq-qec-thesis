"""Analisi osservazionale M11b con effetti fissi per sottografo.

L'``initial_layout`` non garantisce il qubit fisico usato alla misura dopo il routing. Per
questo l'esposizione analizzata e' il readout *effettivo* dei qubit misurati. L'associazione
viene stimata entro sottografo e controllata per numero di ECR e profondita'; non e' una stima
causale dell'effetto di assegnare un ruolo iniziale.
"""

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr


EXPECTED_NOISE_REVISION = 'm11-target-agi-depolarizing-only-v2'
REQUIRED_MANIFEST_KEYS = (
    'circuit_revision', 'noise_model_revision', 'postprocess_revision',
    'circuit_sha256', 'basis_gates', 'optimization_level', 'seed_transpiler',
)


def _safe_spearman(x, y):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if len(x) < 2 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return None
    value = float(spearmanr(x, y).statistic)
    return value if np.isfinite(value) else None


def _within_center(values, groups):
    values = np.asarray(values, dtype=float)
    groups = np.asarray(groups)
    centered = np.empty_like(values)
    for group in np.unique(groups):
        mask = groups == group
        centered[mask] = values[mask] - values[mask].mean()
    return centered


def _residualize(values, controls):
    values = np.asarray(values, dtype=float)
    controls = np.asarray(controls, dtype=float)
    if controls.size == 0 or np.all(np.ptp(controls, axis=0) == 0):
        return values.copy()
    active = np.ptp(controls, axis=0) > 0
    matrix = controls[:, active]
    if matrix.shape[1] == 0:
        return values.copy()
    beta = np.linalg.lstsq(matrix, values, rcond=None)[0]
    return values - matrix @ beta


def _flatten(righe, outcome_partition='holdout'):
    records = []
    for fallback_group, row in enumerate(righe):
        group = int(row.get('subgraph_id', fallback_group))
        for strategy, value in row.get('strategie', {}).items():
            partition = value.get(outcome_partition)
            outcome = (partition.get('P_success') if isinstance(partition, dict)
                       else value.get('P_success'))
            required = (outcome, value.get('readout_misurati'),
                        value.get('n_ecr'), value.get('depth'))
            if any(item is None for item in required):
                continue
            record = {
                'subgraph_id': group,
                'strategy': strategy,
                'P_success': float(outcome),
                'readout_misurati': float(value['readout_misurati']),
                'n_ecr': float(value['n_ecr']),
                'depth': float(value['depth']),
            }
            if all(np.isfinite(required)):
                records.append(record)

    # I gruppi con una sola osservazione non contribuiscono a una stima entro sottografo.
    counts = {}
    for record in records:
        group = record['subgraph_id']
        counts[group] = counts.get(group, 0) + 1
    return [record for record in records if counts[record['subgraph_id']] >= 2]


def _fit_records(records):
    if len(records) < 4:
        raise ValueError('Servono almeno quattro osservazioni valide')
    groups = np.array([r['subgraph_id'] for r in records], dtype=int)
    if len(np.unique(groups)) < 2:
        raise ValueError('Servono almeno due sottografi validi')
    y = np.array([r['P_success'] for r in records])
    readout = np.array([r['readout_misurati'] for r in records])
    ecr = np.array([r['n_ecr'] for r in records])
    depth = np.array([r['depth'] for r in records])

    y_c = _within_center(y, groups)
    readout_c = _within_center(readout, groups)
    ecr_c = _within_center(ecr, groups)
    depth_c = _within_center(depth, groups)
    controls = np.column_stack([ecr_c, depth_c])
    readout_residual = _residualize(readout_c, controls)
    success_residual = _residualize(y_c, controls)
    partial_spearman = _safe_spearman(readout_residual, success_residual)

    design = np.column_stack([readout_c, ecr_c, depth_c])
    beta = np.linalg.lstsq(design, y_c, rcond=None)[0]
    prediction = design @ beta
    denominator = float(np.sum(y_c ** 2))
    r_squared = (1.0 - float(np.sum((y_c - prediction) ** 2)) / denominator
                 if denominator > 0 else None)

    scales_x = np.std(design, axis=0)
    scale_y = float(np.std(y_c))
    standardized = [
        float(beta[i] * scales_x[i] / scale_y) if scale_y > 0 and scales_x[i] > 0 else None
        for i in range(3)
    ]
    return {
        'partial_spearman_readout': partial_spearman,
        'ols_coefficients': {
            'readout_misurati': float(beta[0]),
            'n_ecr': float(beta[1]),
            'depth': float(beta[2]),
        },
        'standardized_coefficients': {
            'readout_misurati': standardized[0],
            'n_ecr': standardized[1],
            'depth': standardized[2],
        },
        'within_r_squared': r_squared,
        'matrix_rank': int(np.linalg.matrix_rank(design)),
    }


def _cluster_bootstrap(records, seed, n_bootstrap, confidence=0.95):
    groups = sorted({r['subgraph_id'] for r in records})
    by_group = {group: [r for r in records if r['subgraph_id'] == group]
                for group in groups}
    rng = np.random.default_rng(seed)
    rho, beta = [], []
    for _ in range(int(n_bootstrap)):
        sampled = rng.choice(groups, size=len(groups), replace=True)
        resampled = []
        # I duplicati bootstrap diventano cluster distinti, non righe dello stesso cluster.
        for new_group, original_group in enumerate(sampled):
            for row in by_group[int(original_group)]:
                copy = dict(row)
                copy['subgraph_id'] = new_group
                resampled.append(copy)
        try:
            fit = _fit_records(resampled)
        except (ValueError, np.linalg.LinAlgError):
            continue
        if fit['partial_spearman_readout'] is not None:
            rho.append(fit['partial_spearman_readout'])
        value = fit['standardized_coefficients']['readout_misurati']
        if value is not None and np.isfinite(value):
            beta.append(value)

    alpha = (1.0 - confidence) / 2.0

    def interval(values):
        if not values:
            return {'ci_low': None, 'ci_high': None, 'n_valid': 0}
        low, high = np.quantile(values, [alpha, 1.0 - alpha])
        return {'ci_low': float(low), 'ci_high': float(high), 'n_valid': len(values),
                'confidence': confidence}

    return {
        'partial_spearman_readout': interval(rho),
        'standardized_readout_coefficient': interval(beta),
    }


def analizza_righe(righe, seed=42, n_bootstrap=2000, outcome_partition='holdout'):
    """Analisi riusabile da CLI, campagna e test."""
    records = _flatten(righe, outcome_partition=outcome_partition)
    fit = _fit_records(records)
    bootstrap = _cluster_bootstrap(records, seed, n_bootstrap)
    groups = np.array([r['subgraph_id'] for r in records])
    y = np.array([r['P_success'] for r in records])
    readout = np.array([r['readout_misurati'] for r in records])
    ecr = np.array([r['n_ecr'] for r in records])
    depth = np.array([r['depth'] for r in records])

    within_ranges = []
    for group in np.unique(groups):
        mask = groups == group
        within_ranges.append(float(y[mask].max() - y[mask].min()))

    strategies = {}
    for name in sorted({r['strategy'] for r in records}):
        values = np.array([r['P_success'] for r in records if r['strategy'] == name])
        strategies[name] = {
            'n': int(len(values)),
            'mean_P_success': float(values.mean()),
            'se_across_subgraphs': (float(values.std(ddof=1) / np.sqrt(len(values)))
                                    if len(values) > 1 else None),
        }

    return {
        'analysis_type': 'observational within-subgraph fixed-effects',
        'outcome_partition': outcome_partition,
        'n_observations': len(records),
        'n_subgraphs': int(len(np.unique(groups))),
        'raw_spearman': {
            'readout_vs_success': _safe_spearman(readout, y),
            'ecr_vs_success': _safe_spearman(ecr, y),
            'depth_vs_success': _safe_spearman(depth, y),
        },
        'controlled_fit': fit,
        'cluster_bootstrap': bootstrap,
        'within_subgraph_success_range': {
            'mean': float(np.mean(within_ranges)),
            'median': float(np.median(within_ranges)),
            'max': float(np.max(within_ranges)),
        },
        'descriptive_by_initial_strategy': strategies,
        'interpretation': (
            'Association with the readout of the qubits actually measured after routing, '
            'controlling for ECR count, depth, and subgraph. Initial-layout labels are '
            'descriptive instruments only; no causal best-vs-worst claim is made.'
        ),
    }


def _print_summary(summary):
    fit = summary['controlled_fit']
    ci = summary['cluster_bootstrap']['partial_spearman_readout']
    print('=== M11b — analisi osservazionale entro sottografo ===')
    print(f"Osservazioni: {summary['n_observations']} | "
          f"sottografi: {summary['n_subgraphs']}")
    print('Spearman parziale readout vs successo '
          f"(controlli ECR/depth): {fit['partial_spearman_readout']}")
    print(f"CI cluster-bootstrap: [{ci['ci_low']}, {ci['ci_high']}]")
    print('Nessun claim causale: l’esposizione e’ il readout effettivo dopo routing.')


def main():
    parser = argparse.ArgumentParser(description='Analisi osservazionale M11b')
    parser.add_argument('--input-json', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--bootstrap', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=None)
    args = parser.parse_args()

    raw = args.input_json.read_bytes()
    payload = json.loads(raw)
    if payload.get('schema_version') != '2.0' or payload.get('milestone') != 'M11b_ruoli':
        raise ValueError('Input incompatibile: richiesti schema 2.0 e milestone M11b_ruoli')
    noise_revision = payload.get('noise_model', {}).get('revision')
    if noise_revision != EXPECTED_NOISE_REVISION:
        raise ValueError(
            f'Input M11b con noise revision incompatibile: {noise_revision!r}'
        )
    manifest = payload.get('manifest')
    if not isinstance(manifest, dict):
        raise ValueError('Input M11b privo di manifest del circuito')
    missing = [key for key in REQUIRED_MANIFEST_KEYS if key not in manifest]
    if missing:
        raise ValueError(f'Manifest M11b incompleto: {", ".join(missing)}')
    calibration_digest = payload.get('backend', {}).get('calibration_sha256')
    if not isinstance(calibration_digest, str) or len(calibration_digest) != 64:
        raise ValueError('Input M11b privo di calibration_sha256 valido')
    embedded_seed = payload.get('design', {}).get(
        'analysis_seed', payload.get('seed', 42)
    )
    seed = int(embedded_seed if args.seed is None else args.seed)
    summary = analizza_righe(payload.get('righe', []), seed=seed,
                             n_bootstrap=args.bootstrap, outcome_partition='holdout')
    _print_summary(summary)

    timestamp = datetime.now().astimezone()
    out = {
        'schema_version': '2.0',
        'milestone': 'M11b_analisi_osservazionale',
        'timestamp': timestamp.isoformat(),
        'source': {
            'path': str(args.input_json.resolve()),
            'sha256': hashlib.sha256(raw).hexdigest(),
            'calibration_sha256': calibration_digest,
            'circuit_manifest': manifest,
        },
        'seed': seed,
        'bootstrap_resamples': args.bootstrap,
        'analysis': summary,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    filename = args.output_dir / f"analysis_M11b_v2_{timestamp:%Y%m%d_%H%M%S}.json"
    with filename.open('w', encoding='utf-8') as stream:
        json.dump(out, stream, indent=2, ensure_ascii=False, allow_nan=False)
    print(f'Analisi salvata in: {filename}')


if __name__ == '__main__':
    main()
