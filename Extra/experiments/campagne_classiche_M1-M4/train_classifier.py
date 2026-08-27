"""
train_classifier.py — Genera il dataset e addestra il classificatore binario.
Eseguire prima di ``rerun_baseline_corretto.py``; ``run_experiments.py`` è legacy.

UC1 e UC2 usano N=15. Il numero di porte effettivo e' registrato nel manifest
dopo la compilazione nella base rz/sx/x/cx; non viene stimato a mano.
UC3 e UC4 (N=21/35) sono esclusi dalle campagne rumorose: l'aritmetica
Beauregard è validata separatamente, ma il circuito compilato è troppo costoso
per la demo e per un confronto NISQ statisticamente utile.
"""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, accuracy_score, roc_auc_score
from sklearn.base import clone
from shor_core import (
    build_noise_model,
    compile_shor_circuit,
    experiment_manifest,
    extract_factors,
    rank_measurements,
)
from qiskit_aer import AerSimulator


CHECKPOINT_REVISION = 'training-dataset-checkpoint-v1'


def _checkpoint_contract(N, a, n_count, noise_base, noise_factor, n_samples,
                         shots, seed, label_top_ks):
    """Contratto esatto che impedisce di riusare un dataset incompatibile."""
    manifest = experiment_manifest(N, a, n_count)
    return {
        'checkpoint_revision': CHECKPOINT_REVISION,
        'N': int(N), 'a': int(a), 'n_count': int(n_count),
        'noise_base': {key: float(value) for key, value in noise_base.items()},
        'noise_factor': float(noise_factor),
        'n_samples': int(n_samples), 'shots': int(shots), 'seed': int(seed),
        'label_top_ks': [int(value) for value in label_top_ks],
        'circuit_sha256': manifest['circuit_sha256'],
        'circuit_revision': manifest['circuit_revision'],
        'noise_model_revision': manifest['noise_model_revision'],
        'postprocess_revision': manifest['postprocess_revision'],
    }


def _save_dataset_checkpoint(path, contract, X, labels):
    """Scrittura atomica: un'interruzione non corrompe l'ultimo checkpoint valido."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    arrays = {
        'contract_json': np.asarray(json.dumps(contract, sort_keys=True)),
        'X': np.asarray(X, dtype=float),
    }
    arrays.update({
        f'label_top_{int(top_k)}': np.asarray(values, dtype=np.int8)
        for top_k, values in labels.items()
    })
    with temporary.open('wb') as stream:
        np.savez_compressed(stream, **arrays)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _load_dataset_checkpoint(path, expected_contract):
    path = Path(path)
    if not path.is_file():
        return None
    try:
        with np.load(path, allow_pickle=False) as payload:
            actual_contract = json.loads(str(payload['contract_json'].item()))
            if actual_contract != expected_contract:
                raise ValueError(
                    f'Checkpoint incompatibile: {path}. Usare --no-resume per rigenerarlo.'
                )
            X = np.asarray(payload['X'], dtype=float)
            labels = {
                top_k: np.asarray(payload[f'label_top_{top_k}'], dtype=int)
                for top_k in expected_contract['label_top_ks']
            }
    except ValueError:
        raise
    except Exception as error:
        raise ValueError(
            f'Checkpoint non leggibile: {path}. Usare --no-resume per rigenerarlo.'
        ) from error

    completed = len(X)
    expected_features = 2 ** expected_contract['n_count']
    if X.ndim != 2 or X.shape[1] != expected_features:
        raise ValueError(f'Checkpoint con feature incompatibili: {path}.')
    if completed > expected_contract['n_samples'] or any(
        len(values) != completed for values in labels.values()
    ):
        raise ValueError(f'Checkpoint con lunghezze incoerenti: {path}.')
    return X, labels


def generate_dataset(N, a, n_count, noise_base, noise_factor=0.5,
                     n_samples=2000, shots=1024, seed=0,
                     label_top_ks=(1, 16), checkpoint_path=None,
                     resume=True, checkpoint_every=200):
    """
    Genera (feature, label) variando i parametri di rumore nell'intorno
    di noise_base entro ±noise_factor (es. 0.5 = ±50%).
    Trasla il circuito una sola volta; varia solo il noise model per campione.
    """
    rng = np.random.default_rng(seed)
    label_top_ks = tuple(sorted(set(int(k) for k in label_top_ks)))
    if not label_top_ks or label_top_ks[0] < 1:
        raise ValueError('label_top_ks deve contenere interi positivi.')
    if type(checkpoint_every) is not int or checkpoint_every < 1:
        raise ValueError('checkpoint_every deve essere un intero positivo.')
    X = []
    labels = {top_k: [] for top_k in label_top_ks}

    # Una sola compilazione deterministica, condivisa con le campagne.
    transpiled_qc = compile_shor_circuit(N, a, n_count)
    print(f"  Circuito traspilato: depth={transpiled_qc.depth()}, "
          f"cx={dict(transpiled_qc.count_ops()).get('cx', 0)}")

    contract = _checkpoint_contract(
        N, a, n_count, noise_base, noise_factor, n_samples,
        shots, seed, label_top_ks,
    )
    if resume and checkpoint_path is not None:
        restored = _load_dataset_checkpoint(checkpoint_path, contract)
        if restored is not None:
            restored_X, restored_labels = restored
            X = [row.copy() for row in restored_X]
            labels = {
                top_k: restored_labels[top_k].astype(int).tolist()
                for top_k in label_top_ks
            }
            # Ogni campione consuma esattamente cinque uniformi prima di Aer.
            # Avanziamo il generatore per conservare la stessa sequenza del run integro.
            rng.uniform(-noise_factor, noise_factor, size=(len(X), 5))
            print(f'  Ripresa da checkpoint: {len(X)}/{n_samples} campioni')

    # Riutilizza un simulatore senza NM; il noise model varia a run-time per campione
    sim = AerSimulator(method='statevector')

    for i in range(len(X), n_samples):
        # Parametri indipendenti: un solo fattore comune correlava artificialmente
        # errori più alti con tempi di coerenza migliori, cancellandone gli effetti.
        factors = 1.0 + rng.uniform(-noise_factor, noise_factor, size=5)
        eps_1q = np.clip(noise_base['eps_1q'] * factors[0], 1e-4, 0.1)
        eps_2q = np.clip(noise_base['eps_2q'] * factors[1], 1e-3, 0.3)
        t1_ns = np.clip(noise_base['t1_ns'] * factors[2], 10_000, 500_000)
        t2_ns = np.clip(noise_base['t2_ns'] * factors[3], 5_000, 2 * t1_ns)
        p_ro = np.clip(noise_base['p_ro'] * factors[4], 0.0, 0.5)

        nm = build_noise_model(eps_1q, eps_2q, t1_ns, t2_ns, p_ro=p_ro)
        # ATTENZIONE — non tornare a `seed_simulator=seed + i`.
        # Aer deriva il generatore del singolo shot come seed_simulator + shot_index:
        # con `shots=1024` due campioni consecutivi condividerebbero 1023 shot su 1024
        # (99.9% di sovrapposizione), rendendo i campioni del dataset fortemente
        # correlati. Lo split train/test finirebbe per separare quasi-duplicati,
        # gonfiando F1 e AUC. Il passo di 10_000 > shots garantisce flussi disgiunti.
        simulation_seed = seed * 1_000_000 + i * 10_000
        counts = sim.run(transpiled_qc, noise_model=nm, shots=shots,
                         seed_simulator=simulation_seed
                         ).result().get_counts()

        sorted_meas = rank_measurements(counts, simulation_seed)
        for top_k in label_top_ks:
            found = any(
                extract_factors(int(ms, 2), n_count, N, a)[0] is not None
                for ms, _ in sorted_meas[:top_k]
            )
            labels[top_k].append(1 if found else 0)

        feature = np.zeros(2 ** n_count)
        for k, v in counts.items():
            feature[int(k, 2)] = v / shots
        X.append(feature)

        if (i + 1) % checkpoint_every == 0 or i + 1 == n_samples:
            if checkpoint_path is not None:
                _save_dataset_checkpoint(checkpoint_path, contract, X, labels)
            balances = ', '.join(
                f'TOP-{top_k}: pos={sum(labels[top_k])} '
                f'neg={i + 1 - sum(labels[top_k])}'
                for top_k in label_top_ks
            )
            print(f"  Campioni: {i+1}/{n_samples} | {balances}")

    return np.array(X), {
        top_k: np.asarray(values, dtype=int)
        for top_k, values in labels.items()
    }


def train_and_save(uc_name, N, a, n_count, noise_base,
                   n_samples=2000, shots=1024, seed=42,
                   output_dir=Path('.'), label_top_ks=(1, 16),
                   noise_factor=0.5, resume=True):
    print(f"\n{'='*55}")
    print(f"Training classificatore per {uc_name}  (N={N}, a={a}, n_count={n_count})")
    print(f"{'='*55}")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    X, labels = generate_dataset(
        N, a, n_count, noise_base,
        n_samples=n_samples, shots=shots, seed=seed,
        label_top_ks=label_top_ks, noise_factor=noise_factor,
        checkpoint_path=output_dir / 'checkpoints' / f'dataset_{uc_name}.npz',
        resume=resume,
    )
    outcomes = {}

    for top_k, y in labels.items():
        pos = int(y.sum())
        balance = {'positive': pos, 'negative': int(len(X) - pos)}
        print(f"\nEtichette TOP-{top_k}: {len(X)} campioni | "
              f"pos={pos} ({100*pos/len(X):.1f}%) "
              f"neg={len(X)-pos} ({100*(1-pos/len(X)):.1f}%)")
        label_dir = output_dir / f'top{top_k}'
        label_dir.mkdir(parents=True, exist_ok=True)
        audit = {
            'schema_version': '2.0',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'use_case': uc_name,
            'label_top_k': int(top_k),
            'class_balance': balance,
            'n_samples': int(n_samples),
            'shots': int(shots),
            'seed': int(seed),
            'noise_base': dict(noise_base),
            'noise_sampling': {
                'distribution': 'independent-uniform-relative',
                'relative_half_width': float(noise_factor),
                'parameters': ['eps_1q', 'eps_2q', 't1_ns', 't2_ns', 'p_ro'],
            },
            'manifest': experiment_manifest(N, a, n_count),
        }

        if pos == 0 or pos == len(X):
            audit['trainable'] = False
            audit['reason'] = 'single-class-dataset'
            print("  Classe unica: classificatore non addestrabile (esito registrato).")
            with (label_dir / f'label_audit_{uc_name}.json').open(
                'w', encoding='utf-8'
            ) as stream:
                json.dump(audit, stream, indent=2)
            outcomes[top_k] = audit
            continue

        # Split 60/20/20: il test non partecipa alla scelta dell'algoritmo.
        X_dev, X_te, y_dev, y_te = train_test_split(
            X, y, test_size=0.2, random_state=seed, stratify=y
        )
        X_tr, X_val, y_tr, y_val = train_test_split(
            X_dev, y_dev, test_size=0.25, random_state=seed, stratify=y_dev
        )
        candidates = {
            'RandomForest': RandomForestClassifier(
                n_estimators=200, random_state=seed, n_jobs=-1
            ),
            'SVM': CalibratedClassifierCV(
                SVC(kernel='rbf', random_state=seed),
                method='sigmoid', cv=3,
            ),
            'MLP': MLPClassifier(
                hidden_layer_sizes=(256, 128), max_iter=500, random_state=seed
            ),
        }
        best_name, best_clf, best_f1 = None, None, -1
        validation_metrics = {}
        for name, clf in candidates.items():
            clf.fit(X_tr, y_tr)
            preds = clf.predict(X_val)
            f1 = f1_score(y_val, preds, zero_division=0)
            acc = accuracy_score(y_val, preds)
            try:
                auc = roc_auc_score(y_val, clf.predict_proba(X_val)[:, 1])
            except Exception:
                auc = float('nan')
            validation_metrics[name] = {'f1': f1, 'acc': acc, 'auc': auc}
            print(f"  validation {name}: F1={f1:.3f}  "
                  f"Acc={acc:.3f}  AUC={auc:.3f}")
            if f1 > best_f1:
                best_name, best_clf, best_f1 = name, clf, f1

        # Refit su train+validation, quindi unica valutazione finale sul test.
        best_clf = clone(candidates[best_name]).fit(X_dev, y_dev)
        test_preds = best_clf.predict(X_te)
        test_f1 = f1_score(y_te, test_preds, zero_division=0)
        test_acc = accuracy_score(y_te, test_preds)
        try:
            test_auc = roc_auc_score(y_te, best_clf.predict_proba(X_te)[:, 1])
        except Exception:
            test_auc = float('nan')
        test_metrics = {'f1': test_f1, 'acc': test_acc, 'auc': test_auc}
        metrics = {'validation': validation_metrics, 'test': test_metrics}
        print(f">> TOP-{top_k}, selezionato su validation: {best_name}; "
              f"test F1={test_f1:.3f}, Acc={test_acc:.3f}, AUC={test_auc:.3f}")
        model_payload = {
            **audit,
            'trainable': True,
            'label_rule': f'at-least-one-valid-factor-in-top-{top_k}',
            'clf': best_clf,
            'name': best_name,
            'metrics': metrics,
            'X_test': X_te,
            'y_test': y_te,
        }
        fname = label_dir / f"clf_{uc_name}.joblib"
        joblib.dump(model_payload, fname)
        print(f"   Salvato in {fname}")
        outcomes[top_k] = {**audit, 'trainable': True, 'metrics': metrics,
                           'selected_model': best_name, 'model_path': str(fname)}

    return outcomes


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--n-samples', type=int, default=2000)
    parser.add_argument('--shots', type=int, default=1024)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output-dir', type=Path, default=Path('.'))
    parser.add_argument('--label-top-k', type=int, nargs='+', default=[1, 16])
    parser.add_argument(
        '--noise-factor', type=float, default=0.5,
        help='Semiampiezza relativa del campionamento uniforme indipendente.',
    )
    parser.add_argument(
        '--no-resume', action='store_true',
        help='Ignora e sovrascrive i checkpoint dataset compatibili.',
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = _parse_args()
    if args.n_samples < 10 or args.shots < 1:
        raise ValueError('n-samples deve essere >=10 e shots deve essere positivo.')
    if not 0 <= args.noise_factor <= 1:
        raise ValueError('noise-factor deve essere compreso tra 0 e 1.')
    NOISE_REALISTIC = {'eps_1q': 1e-3, 'eps_2q': 1e-2,
                       't1_ns': 100_000, 't2_ns': 80_000, 'p_ro': 0.02}
    NOISE_DEGRADED  = {'eps_1q': 5e-3, 'eps_2q': 5e-2,
                       't1_ns': 50_000,  't2_ns': 30_000,  'p_ro': 0.05}

    outcomes = {}
    outcomes['UC1'] = train_and_save(
        'UC1', N=15, a=7, n_count=8, noise_base=NOISE_REALISTIC,
        n_samples=args.n_samples, shots=args.shots, seed=args.seed,
        output_dir=args.output_dir, label_top_ks=args.label_top_k,
        noise_factor=args.noise_factor, resume=not args.no_resume,
    )
    outcomes['UC2'] = train_and_save(
        'UC2', N=15, a=7, n_count=8, noise_base=NOISE_DEGRADED,
        n_samples=args.n_samples, shots=args.shots, seed=args.seed,
        output_dir=args.output_dir, label_top_ks=args.label_top_k,
        noise_factor=args.noise_factor, resume=not args.no_resume,
    )

    summary = {
        'schema_version': '2.0',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'n_samples_per_use_case': args.n_samples,
        'shots': args.shots,
        'seed': args.seed,
        'noise_factor': args.noise_factor,
        'label_top_k': sorted(set(args.label_top_k)),
        'checkpoint_revision': CHECKPOINT_REVISION,
        'manifest': experiment_manifest(),
        'outcomes': outcomes,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / 'training_manifest.json').open(
        'w', encoding='utf-8'
    ) as stream:
        json.dump(summary, stream, indent=2)

    print("\n--- UC3/UC4 (N=21/35): skip training ---")
    print("L'aritmetica Beauregard è validata separatamente, ma N=21 richiede 21.036 CX")
    print("nella base RZ/SX/X/CX (n_count=8): escluso dal training rumoroso per costo.")
