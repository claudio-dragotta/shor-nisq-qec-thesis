# M7 — Surface code (Stim + PyMatching)

**Blocco M7** del documento di indirizzo (§10). Codice topologico scalabile: stima del
**logical error rate** p_L con un decoder reale (MWPM) e osservazione del **comportamento a soglia**.

## Cos'è e a cosa serve

Il surface code è il codice fault-tolerant di riferimento dell'industria: qubit dati e qubit di
misura su una griglia 2D, stabilizzatori locali estratti ciclicamente. Aumentando la distanza d
si riduce l'errore logico — **ma solo se p è sotto una soglia**. Serve a mostrare
quantitativamente:
1. che esiste una **soglia** p_th sotto cui codificare conviene (e crescere in d aiuta);
2. quale p_L è raggiungibile a un dato p fisico → dato che alimenta lo Shor logico (M8).

A differenza di M5/M6 (Qiskit statevector), qui si usa **Stim** (simulatore stabilizzatore
velocissimo) e **PyMatching** (decoder Minimum Weight Perfect Matching), gli standard del settore.

## File

| File | Cos'è |
|---|---|
| `qec_surface.py` | Costruisce il surface code (Stim), decodifica MWPM (PyMatching), curva p vs p_L per d=3,5,7 |
| `results_M7_surface_z_*.json` | Risultati in base memory Z |
| `results_M7_surface_x_*.json` | Risultati in base memory X |

## Prerequisito ambiente

```bash
pip install stim pymatching     # oltre a quanto già in ../requirements.txt
```

## Come si esegue

```bash
source ~/quantum-env/bin/activate
python qec_surface.py --basis z --shots 200000    # base Z (default)
python qec_surface.py --basis x --shots 200000    # base X
# opzioni: --distances 3 5 7   --shots N   --seed S
```
Figura per la tesi: `../../../figure_src/gen_qec_surface.py` → `file_latex/figure/qec_surface_curve.pdf`.

## Cosa aspettarsi (flag)

### Sanity (p piccolo)
A p basso, distanza maggiore ⟹ errore logico minore.
- 🟢 **VERDE** se a p=0.002: p_L(d=3) > p_L(d=5) > p_L(d=7).

### Flag decisivo: la soglia
Le curve d=3,5,7 devono **incrociarsi** a una soglia p_th.
- 🟢 **VERDE** se esiste un p dove l'ordinamento si inverte (sotto: d↑⇒p_L↓; sopra: d↑⇒p_L↑).
- 🔴 **ROSSO** se d maggiore dà p_L peggiore ovunque → decoder o DEM sbagliato; oppure p_L>0 a
  rumore nullo.

### Risultati ottenuti (200k shot)
- **Soglia**: p_th ≈ 0.9% (base Z), ≈ 0.7% (base X) — coerente con la letteratura (MWPM,
  circuit-level).
- **Soppressione sotto soglia** (p=0.002): p_L = 1.9e-3 (d3) → 4.4e-4 (d5) → 1.1e-4 (d7),
  fattore ~4 per incremento di distanza.
- **Inversione sopra soglia** (p=0.01): p_L = 3.8% (d3) < 5.2% (d7).

## Come leggere i JSON

```
{"curve": {"basis": "z", "shots": 200000, "threshold": 0.009,
           "sanity_ok": true,
           "table": {"3": [{"p":0.002,"p_L":0.00194,"p_L_se":0.0001}, ...],
                     "5": [...], "7": [...]}}}
```
- `sanity_ok: true` → flag sanity VERDE.
- `threshold` → soglia stimata (incrocio d_min/d_max). Se `null`, nessun incrocio nel range.
- Per ogni distanza, `table[d]` è la curva p→p_L con deviazione standard `p_L_se`.

## Collegamento a M8

Il p_L raggiungibile nel regime sotto-soglia (es. ~1e-4 a p=0.002, d=7) è il tasso di errore per
gate logico che lo **Shor logico** (M8) inietterà per stimare quale p_L serve a P_success ≥ 80%.
