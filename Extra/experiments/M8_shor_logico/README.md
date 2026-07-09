# M8 — Shor logico: integrazione a livelli — ⬜ DA FARE

**Blocco M8** del documento di indirizzo (§11). Chiude l'arco della tesi collegando Shor rumoroso
(M1–M4) e la correzione d'errore (M5–M7) tramite il **logical error rate** p_L.

## Cosa conterrà

- `shor_logico.py` — inietta un errore logico p_L dopo ogni gate/blocco logico nel circuito di
  Shor esistente (riusa `campagne_classiche_M1-M4/shor_core.py`) e misura P_success in funzione
  di p_L.
- `results_M8_shor_logico_*.json` — P_success vs p_L.
- Figura conclusiva: Shor fisico rumoroso vs Steane vs surface code.

## Cosa aspettarsi (flag)

- **Sanity** a p_L=0: P_success = valore ideale (≈100% per N=15).
- **Monotonìa**: P_success decresce al crescere di p_L.
- **Domanda conclusiva**: quale p_L serve perché P_success ≥ 80%? → p_L*.
- **Chiusura dell'arco**: p_L* deve essere **raggiungibile** dal surface code (M7) per qualche
  coppia (d, p) fisica sensata. Se sì, la tesi risponde: "servono qubit logici a p_L*,
  ottenibili con surface code d=… a errore fisico p=…".

Dettagli e criteri in `../../../piano_azione_qec.md` (Parte V, sezione M8).

> Nota metodologica (documento §11): l'integrazione è **a livelli**, mai "Shor fault-tolerant
> completo" simulato esplicitamente (intrattabile su hardware classico). Si stima p_L dalla QEC
> isolata e lo si inietta come errore logico equivalente.
