# Demo interattiva della tesi

App Streamlit in 7 tab: il problema (Shor su NISQ), un **simulatore live** con
Qiskit + Qiskit Aer (rumore configurabile globale, per-qubit e per-gate), la
strategia TOP-K, l'ablazione del classificatore ML, la scala QEC (repetition →
Steane → surface), lo Shor logico con la figura conclusiva, e il bilancio finale.

- I tab 1, 3-7 leggono **solo** i JSON già presenti in `../experiments/` (M1-M8)
  e i numeri già validati e riportati in tesi (Cap. 10, Cap. 13) — nessuna
  dipendenza da Qiskit a runtime per quella parte.
- Il tab 2 ("Simulatore live") esegue **dal vivo** il vero circuito di Shor
  (N=15, a=7) con Qiskit + Qiskit Aer, riusando `shor_core.py` delle campagne
  ufficiali M1-M4 — non un'implementazione parallela. Richiede quindi
  qiskit/qiskit-aer (nel `requirements.txt`).

## Avvio locale (senza Docker)

```bash
cd Extra/demo
pip install -r requirements.txt
streamlit run app.py
```

Si apre su `http://localhost:8501`.

## Avvio con Docker (consigliato — ambiente riproducibile, stesse versioni della tesi)

Il contesto di build è la **root del repo** (serve a includere `Extra/experiments/`).

```bash
# dalla root del repo
docker build -f Extra/demo/Dockerfile -t tesi-demo .
docker run -p 8501:8501 tesi-demo
```

oppure con Docker Compose (da `Extra/demo/`):

```bash
cd Extra/demo
docker compose up --build
```

Si apre su `http://localhost:8501`.

### Nota tecnica: perché il simulatore live gira in un sottoprocesso

Qiskit Aer (metodo `matrix_product_state`) va in **Segmentation fault** se
costruito ed eseguito nel thread interno di Streamlit (`ScriptRunner`) — bug
riprodotto e isolato durante lo sviluppo: la stessa identica chiamata, con gli
stessi parametri, funziona sempre se lanciata come processo Python normale
(anche ripetuta decine di volte), ma crasha sistematicamente nel thread di
Streamlit. La soluzione adottata in `quantum_backend.py`
(`run_comparison_isolated` / `list_gates_isolated`) esegue ogni chiamata a
Qiskit in un **sottoprocesso** dedicato (interprete e thread principale
propri), che aggira il problema. Se in futuro sposti la logica di simulazione,
mantieni questo pattern.

## Deploy su Render (sito pubblico)

Render supporta il deploy diretto da Dockerfile:

1. Pusha il repo (o almeno `Extra/`, `.dockerignore`, e i file necessari — vedi
   sotto) su GitHub/GitLab.
2. Su Render: **New → Web Service** → connetti il repo.
3. **Runtime**: Docker. **Dockerfile path**: `Extra/demo/Dockerfile`.
   **Docker build context**: la root del repo (Render lo chiede esplicitamente
   in "Root Directory" — lascialo vuoto/`.` per usare la root).
4. Render inietta automaticamente `$PORT`: il Dockerfile lo usa già
   (`CMD streamlit run app.py --server.port=$PORT ...`), non serve configurare
   nulla.
5. Piano: il simulatore live è leggero (N=15, ~12 qubit, run in pochi secondi),
   va bene anche il piano gratuito/starter — ma il **primo** avvio a freddo può
   impiegare 1-2 minuti (cold start + build immagine).

Non serve un database né storage persistente: tutto quello che serve (JSON dei
risultati M1-M8, script Shor) è già dentro l'immagine.

## Se aggiungi nuovi risultati (M9, rifiniture)

I loader in `data.py` cercano i file con un pattern glob (es.
`results_M5_repetition_{basis}_*.json`): un nuovo run con timestamp diverso
viene raccolto automaticamente, non serve modificare l'app (né il Dockerfile,
che copia `*.json` per cartella). Se cambia lo *schema* di un JSON (nuove
chiavi), aggiorna il loader corrispondente in `data.py`.

I numeri dell'ablazione TOP-K/ML (tab 3-4) e i valori dei tre regimi nello
Shor logico (tab 6) sono presi **letteralmente** da
`file_latex/capitoli/RisultatiSperimentali.tex` (tab:riepilogo_rho) e
`file_latex/capitoli/ShorLogico.tex` (fig:qec_shor_logico): se quei numeri
cambiano in tesi, aggiorna `ABLATION_TABLE` e `SHOR_LOGICO_REGIMES` in
`data.py` di conseguenza.
