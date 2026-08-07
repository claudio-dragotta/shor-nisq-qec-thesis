# Guida agli esperimenti di analisi parametrica

## Cosa abbiamo aggiunto

### Nel LaTeX (`file_latex/capitoli/ConclusioniMetodo2.tex`)

Nuova sezione: **"Analisi Sperimentale dei Parametri di Mitigazione"**

Contiene 7 tabelle con struttura pronta, da riempire con i risultati degli esperimenti:

| Tabella | Label LaTeX | Parametro variato |
|---|---|---|
| Tab. sweep_k | `tab:sweep_k` | K = 1, 2, 3, 4, 6, 8 |
| Tab. sweep_eps | `tab:sweep_eps` | ε₂q = 0.001 → 0.1 |
| Tab. sweep_shots | `tab:sweep_shots` | shots = 128, 256, 512, 1024, 2048 |
| Tab. sweep_joint | `tab:sweep_joint` | Griglia K × ε₂q (4×4) |
| Tab. sweep_t1 | `tab:sweep_t1` | T₁ = 20, 50, 100, 200, 500 µs |
| Tab. sweep_eps1q | `tab:sweep_eps1q` | ε₁q = 0.0001 → 0.02 |
| Tab. sweep_pro | `tab:sweep_pro` | p_ro = 0%, 1%, 2%, 5%, 10%, 20% |

I valori di riferimento UC1 (già noti) sono precompilati nelle tabelle come riga di riferimento.

### Il nuovo script (`experiments/run_parameter_analysis.py`)

7 sweep indipendenti, eseguibili tutti insieme o uno alla volta.

---

## Come eseguire

### Prerequisiti
```bash
source ~/quantum-env/bin/activate
cd ~/path/to/experiments
```

### Eseguire tutto (lungo, circa 2-4 ore)
```bash
python run_parameter_analysis.py
```

### Eseguire uno sweep alla volta (consigliato)
```bash
python run_parameter_analysis.py --sweep k
python run_parameter_analysis.py --sweep eps
python run_parameter_analysis.py --sweep shots
python run_parameter_analysis.py --sweep joint
python run_parameter_analysis.py --sweep t1t2
python run_parameter_analysis.py --sweep eps1q
python run_parameter_analysis.py --sweep pro
```

### Output
- File JSON con tutti i dati: `results_parameter_analysis_YYYYMMDD_HHMMSS.json`
- **Righe LaTeX pronte** stampate a terminale dopo ogni sweep

---

## Cosa aspettarsi dai risultati

### Sweep K (priorità alta)

K varia il numero di candidati tentati per iterazione.

| K | Previsione |
|---|---|
| 1 | Identico a M1: M̄ ≈ 1.97, sr = 100% |
| 2 | Miglioramento parziale: M̄ tra 2 e 4 |
| 3 | Miglioramento significativo: M̄ intorno a 1-2 |
| 4 | M̄ = 1.00, sr = 100% (già noto) |
| 6 | M̄ = 1.00, sr = 100% (nessun guadagno aggiuntivo) |
| 8 | M̄ = 1.00, sr = 100% (nessun guadagno aggiuntivo) |

**Conclusione attesa**: il ginocchio della curva è a K=4=r. Questo conferma che K=r è il valore ottimale.

---

### Sweep ε₂q (priorità alta)

ε₂q è il parametro dominante. Si cerca la soglia critica.

| ε₂q | P_surv | Previsione M̄ TOP4 |
|---|---|---|
| 0.001 | 85% | 1.00, sr ≈ 100% |
| 0.005 | 45% | 1.00, sr ≈ 100% |
| 0.01 | 19.7% | 1.00, sr = 100% (noto) |
| 0.02 | 3.9% | 1.00 o leggermente > 1 |
| 0.05 | 0.025% | 1.00, sr = 100% (noto da UC2) |
| 0.10 | ~8e-8 | degradazione attesa, M̄ > 1 o sr < 100% |

**Conclusione attesa**: TOP-4 funziona fino a ε₂q ≈ 0.05. A 0.10 probabilmente degrada.

---

### Sweep shots (priorità media)

| shots | Previsione |
|---|---|
| 128 | Istogramma molto sparso, sr < 100%, M̄ > 1 |
| 256 | Istogramma sparso, sr probabilmente < 100% |
| 512 | Borderline, potrebbe funzionare |
| 1024 | M̄ = 1.00, sr = 100% (noto) |
| 2048 | M̄ = 1.00, sr = 100% (nessun guadagno) |

**Conclusione attesa**: la soglia minima è intorno a 512-1024 shot.

---

### Sweep joint K × ε₂q (priorità alta)

Verifica se K alto compensa rumore elevato.

**Previsione**: per ε₂q = 0.05 (UC2), K=4 già basta. Per ε₂q = 0.10 (fuori range testato), K più alto potrebbe aiutare ma è probabile che l'istogramma sia troppo piatto per qualsiasi K.

---

### Sweep T₁/T₂ (priorità bassa)

**Previsione forte**: nessuna variazione significativa di M̄. Il tempo totale di gate per N=15 è ~8 µs, molto inferiore anche al T₁ minimo testato (20 µs). La tabella dovrebbe mostrare M̄ ≈ 1.00 e sr ≈ 100% per tutti i valori.

**Se questa previsione è confermata**: è un risultato importante — significa che per N=15 il rilassamento termico è irrilevante e il collo di bottiglia è solo ε₂q.

---

### Sweep ε₁q (priorità bassa)

**Previsione forte**: nessuna variazione significativa. Le porte a singolo qubit sono poche rispetto alle 162 CX. La curva dovrebbe essere piatta fino a ε₁q ≈ ε₂q = 0.01, e degradare solo per ε₁q > 0.01 (ovvero quando l'errore singolo qubit diventa comparabile a quello a due qubit).

---

### Sweep p_ro (priorità bassa)

**Previsione**: degrado graduale del sr per p_ro > 10%. Ogni bit flippato sposta la stringa misurata di un valore diverso nel registro a 8 bit, allargando i picchi. TOP-4 dovrebbe compensare fino a p_ro ≈ 10-15%.

---

## Come riempire le tabelle LaTeX

Dopo ogni sweep, lo script stampa righe LaTeX già formattate come:

```
2 & 85.0\% & 3.12 & 4.21 & 2.060 & $0.045$ (sign.) \\
```

Copia queste righe direttamente nelle tabelle corrispondenti in `ConclusioniMetodo2.tex`.

Le righe di riferimento (K=4 o UC1) sono già presenti nelle tabelle — non sovrascriverle.

---

## Ordine consigliato di esecuzione

1. **`--sweep k`** — il più importante, conferma la teoria su K=r
2. **`--sweep eps`** — trova la soglia critica, risultato chiave
3. **`--sweep joint`** — completa il quadro K vs rumore
4. **`--sweep shots`** — utile per raccomandazioni pratiche
5. **`--sweep eps1q`** — conferma che è parametro secondario
6. **`--sweep t1t2`** — conferma che è parametro secondario
7. **`--sweep pro`** — conferma che è parametro secondario
