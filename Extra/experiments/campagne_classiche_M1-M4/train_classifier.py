"""
train_classifier.py — Genera il dataset e addestra il classificatore binario.
Eseguire una volta per use case prima di run_experiments.py.

UC1 e UC2 usano N=15 (circuiti efficienti, ~6 porte CX).
UC3 e UC4 (N=21/35) sono esclusi per circuit depth eccessiva (>8000 CX dopo sintesi
UnitaryGate): entrambi i metodi falliscono sotto rumore NISQ — cf. analisi scalabilità.
"""
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, accuracy_score, roc_auc_score
from shor_core import build_noise_model, shor_circuit, extract_factors
from qiskit import transpile
from qiskit_aer import AerSimulator


def generate_dataset(N, a, n_count, noise_base, noise_factor=0.5,
                     n_samples=2000, shots=1024, seed=0):
    """
    Genera (feature, label) variando i parametri di rumore nell'intorno
    di noise_base entro ±noise_factor (es. 0.5 = ±50%).
    Trasla il circuito una sola volta; varia solo il noise model per campione.
    """
    rng = np.random.default_rng(seed)
    X, y = [], []

    # Trasla con il noise model di riferimento e opt=2 per decomporre CCX → CX
    nm_ref = build_noise_model(**noise_base)
    sim_for_tp = AerSimulator(noise_model=nm_ref, method='statevector')
    transpiled_qc = transpile(shor_circuit(N, a, n_count), sim_for_tp,
                              optimization_level=2)
    print(f"  Circuito traspilato: depth={transpiled_qc.depth()}, "
          f"cx={dict(transpiled_qc.count_ops()).get('cx', 0)}")

    # Riutilizza un simulatore senza NM; il noise model varia a run-time per campione
    sim = AerSimulator(method='statevector')

    for i in range(n_samples):
        factor = 1.0 + rng.uniform(-noise_factor, noise_factor)
        eps_1q = np.clip(noise_base['eps_1q'] * factor, 1e-4, 0.1)
        eps_2q = np.clip(noise_base['eps_2q'] * factor, 1e-3, 0.3)
        t1_ns  = np.clip(noise_base['t1_ns']  * factor, 10_000, 500_000)
        t2_ns  = np.clip(noise_base['t2_ns']  * factor, 5_000,  t1_ns)

        nm = build_noise_model(eps_1q, eps_2q, t1_ns, t2_ns, p_ro=noise_base['p_ro'])
        # ATTENZIONE — non tornare a `seed_simulator=seed + i`.
        # Aer deriva il generatore del singolo shot come seed_simulator + shot_index:
        # con `shots=1024` due campioni consecutivi condividerebbero 1023 shot su 1024
        # (99.9% di sovrapposizione), rendendo i campioni del dataset fortemente
        # correlati. Lo split train/test finirebbe per separare quasi-duplicati,
        # gonfiando F1 e AUC. Il passo di 10_000 > shots garantisce flussi disgiunti.
        counts = sim.run(transpiled_qc, noise_model=nm, shots=shots,
                         seed_simulator=seed * 1_000_000 + i * 10_000
                         ).result().get_counts()

        # Label = 1 se almeno uno dei TOP_K=16 candidati dà fattori validi.
        # TOP_K=16 (coarse gate): classifica se l'istogramma contiene segnale QPE.
        # M2 usa poi top_k=4 (fine search) sulle iterazioni accettate.
        TOP_K = 16
        sorted_meas = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        found = any(
            extract_factors(int(ms, 2), n_count, N, a)[0] is not None
            for ms, _ in sorted_meas[:TOP_K]
        )
        label = 1 if found else 0

        feature = np.zeros(2 ** n_count)
        for k, v in counts.items():
            feature[int(k, 2)] = v / shots
        X.append(feature)
        y.append(label)

        if (i + 1) % 200 == 0:
            pos = sum(y)
            print(f"  Campioni: {i+1}/{n_samples} | pos={pos} neg={len(y)-pos} "
                  f"({100*pos/(i+1):.1f}% positivi)")

    return np.array(X), np.array(y)


def train_and_save(uc_name, N, a, n_count, noise_base,
                   n_samples=2000, shots=1024, seed=42):
    print(f"\n{'='*55}")
    print(f"Training classificatore per {uc_name}  (N={N}, a={a}, n_count={n_count})")
    print(f"{'='*55}")
    X, y = generate_dataset(N, a, n_count, noise_base,
                             n_samples=n_samples, shots=shots, seed=seed)
    pos = y.sum()
    print(f"\nDataset finale: {len(X)} campioni | pos={pos} ({100*pos/len(X):.1f}%)"
          f" neg={len(X)-pos} ({100*(1-pos/len(X)):.1f}%)")

    if pos == 0 or pos == len(X):
        print("  ATTENZIONE: classe unica nel dataset — classificatore inutile, skip.")
        return None, {}

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y)

    candidates = {
        'RandomForest': RandomForestClassifier(n_estimators=200, random_state=seed,
                                               n_jobs=-1),
        'SVM':          SVC(kernel='rbf', probability=True, random_state=seed),
        'MLP':          MLPClassifier(hidden_layer_sizes=(256, 128),
                                      max_iter=500, random_state=seed),
    }
    best_name, best_clf, best_f1 = None, None, -1
    metrics = {}
    for name, clf in candidates.items():
        clf.fit(X_tr, y_tr)
        preds = clf.predict(X_te)
        f1  = f1_score(y_te, preds, zero_division=0)
        acc = accuracy_score(y_te, preds)
        try:
            auc = roc_auc_score(y_te, clf.predict_proba(X_te)[:, 1])
        except Exception:
            auc = float('nan')
        metrics[name] = {'f1': f1, 'acc': acc, 'auc': auc}
        print(f"  {name}: F1={f1:.3f}  Acc={acc:.3f}  AUC={auc:.3f}")
        if f1 > best_f1:
            best_name, best_clf, best_f1 = name, clf, f1

    print(f">> Selezionato: {best_name}  F1={best_f1:.3f}")
    fname = f"clf_{uc_name}.joblib"
    joblib.dump({'clf': best_clf, 'name': best_name, 'metrics': metrics,
                 'X_test': X_te, 'y_test': y_te}, fname)
    print(f"   Salvato in {fname}")
    return best_clf, metrics


if __name__ == '__main__':
    NOISE_REALISTIC = {'eps_1q': 1e-3, 'eps_2q': 1e-2,
                       't1_ns': 100_000, 't2_ns': 80_000, 'p_ro': 0.02}
    NOISE_DEGRADED  = {'eps_1q': 5e-3, 'eps_2q': 5e-2,
                       't1_ns': 50_000,  't2_ns': 30_000,  'p_ro': 0.05}

    train_and_save('UC1', N=15, a=7, n_count=8, noise_base=NOISE_REALISTIC,
                   n_samples=2000, shots=1024)
    train_and_save('UC2', N=15, a=7, n_count=8, noise_base=NOISE_DEGRADED,
                   n_samples=2000, shots=1024)

    print("\n--- UC3/UC4 (N=21/35): skip training ---")
    print("Circuiti UnitaryGate producono >8000 porte CX dopo traspilosizione Qiskit.")
    print("Con eps_2q=0.01 e 8000 porte: P(survival) = (0.99)^8000 ≈ 0%.")
    print("Entrambi i metodi falliscono — analisi scalabilità riportata nei capitoli 12-13.")
