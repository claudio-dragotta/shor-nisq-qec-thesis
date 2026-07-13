# M8 — Shor logico: integrazione a livelli

**Blocco M8** del documento di indirizzo (§11). Chiude l'arco della tesi: unisce Shor (M1–M4)
e la correzione d'errore (M5–M7) tramite il **logical error rate** p_L, con un modello A LIVELLI.

## Cos'è e a cosa serve

Non si codifica esplicitamente ogni qubit di Shor (intrattabile su hardware classico). Si
inietta invece un **errore logico equivalente p_L** dopo ogni gate del circuito di Shor e si
misura la probabilità di successo. La domanda del documento: *quale p_L serve perché Shor
mantenga P_success alta?* La risposta, combinata con i risultati del surface code (M7), dice
quanti qubit fisici servirebbero.

Produce la **figura conclusiva della tesi**: P_success di Shor in funzione di p_L, con i tre
regimi di correzione a confronto (fisico nudo → Steane → surface code).

## File

| File | Cos'è |
|---|---|
| `shor_logico.py` | Inietta p_L per gate su Shor N=15, curva P_success vs p_L (metrica per-misura) |
| `results_M8_shor_logico_*.json` | Curva P_success vs p_L |

Riusa il circuito di Shor da `../campagne_classiche_M1-M4/shor_core.py` (via `sys.path`).

## Come si esegue

```bash
source ~/quantum-env/bin/activate
python shor_logico.py                 # N=15, curva per-misura (16384 shot/punto)
# opzioni: --N --a --n_count --shots --seed
```

Figura conclusiva: `../../../figure_src/gen_shor_logico.py`
→ `file_latex/figure/qec_shor_logico_curve.pdf`.

## Metrica: perché "per singola misura" e non TOP-4

P_success = frazione di **misure** che ricostruiscono i fattori corretti. Si è scelta questa
metrica (un grande run per punto) invece della ricerca multi-candidato TOP-4 perché su N=15 il
period finding è **degenere** (periodo r=4: troppi esiti portano ai fattori). Con TOP-4,
P_success non scende sotto l'80% nemmeno a p_L alto e la curva risulta **non monotòna** —
inutilizzabile. La metrica per-misura è monotòna e interpretabile.

## Cosa aspettarsi (flag)

- 🟢 **Monotonìa**: P_success decresce con p_L (verificato: VERDE).
- **Limite intrinseco** (p_L→0): ~0.75 per N=15 (una singola misura di Shor non dà mai 100%).
- **Plateau casuale** (p_L alto): ~0.25 (istogramma uniforme).
- **Regimi** (dai risultati M6/M7): fisico nudo p_L~10⁻²→P≈0.64; Steane p_L~1.7e-3→P≈0.72;
  surface d=7 p_L~10⁻⁴→P≈0.74.

## Barriera di scalabilità (perché solo N=15)

Lo sweep su N crescente (indicazione del prof) mostra il muro **subito a N=21**: il circuito,
dopo transpilazione (Beauregard), ha profondità ~9500 su 22 qubit → la simulazione classica non
completa nemmeno un run senza rumore. Coerente col documento (§2.2: N=21/35 "se gestibili") e
con la barriera già documentata in tesi per UC3/UC4. La finestra simulabile si esaurisce a N=15;
la scala reale si affronta con le resource estimates (Gidney-Ekerå), non con la simulazione.

## Come leggere il JSON

```
{"curve": {"N": 15, "shots": 16384, "monotonic": true,
           "P_ideal": 0.752, "P_floor": 0.249,
           "points": [{"p_L": 0.01, "P_success": 0.6436, "P_success_se": 0.0037}, ...]}}
```
- `monotonic: true` → flag VERDE.
- `P_ideal` = limite a p_L→0 (0.75); `P_floor` = plateau casuale (0.25).
