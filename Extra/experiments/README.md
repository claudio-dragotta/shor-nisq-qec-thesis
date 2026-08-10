# experiments/ — codice sperimentale della tesi (Shor + QEC)

Indice dei blocchi sperimentali. Ogni blocco (milestone **M**) ha una cartella dedicata con
il codice, i risultati (JSON) e un README che spiega **cosa fa, cosa aspettarsi e come leggere
i risultati**. Le milestone seguono il documento di indirizzo del relatore (`M0`–`M9`); lo stato
e i criteri di validazione (flag 🟢/🔴) sono in `../../piano_azione_qec.md` (Parte V).

## Ambiente

```bash
source ~/quantum-env/bin/activate        # WSL
# se l'ambiente non esiste:
python3 -m venv ~/quantum-env && source ~/quantum-env/bin/activate
pip install -r requirements.txt
```

`requirements.txt` (in questa cartella) fissa le versioni: qiskit 2.5.0, qiskit-aer 0.17.2,
numpy, scipy, matplotlib. Per M7 servirà in aggiunta `pip install stim pymatching`
(stim 1.16.0, PyMatching 2.4.0), e per M10 anche `pip install scikit-learn`.

## Mappa dei blocchi

| Cartella | Blocco | Contenuto | Stato |
|---|---|---|---|
| `campagne_classiche_M1-M4/` | M1–M4 | Shor ideale/rumoroso, Metodo 1/2, TOP-4, campagna parametrica, ZNE | ✅ fatto (prima campagna) |
| `M5_repetition_code/` | M5 | Codice a ripetizione a 3 qubit (bit-flip + phase-flip) | ✅ completo |
| `M6_steane_code/` | M6 | Codice di Steane [[7,1,3]] (codice QEC centrale) | ✅ completo |
| `M7_surface_code/` | M7 | Surface code con Stim + PyMatching (soglia p_th≈0.8%) | ✅ completo |
| `M8_shor_logico/` | M8 | Shor logico: P_success vs p_L + figura conclusiva | ✅ completo |
| `M10_neural_decoder/` | M10 | Decodifica appresa vs MWPM — 12 esperimenti in tre ondate: il risultato (E1–E4), gli attacchi al risultato (E5–E7), gli attacchi alle conclusioni (E8–E12) | ✅ completo |
| `M12_coerenti/` | M12 | Il decoder appreso guadagna di più sugli errori coerenti? (no: il ciclo QEC li converte in statistica di Pauli) | ✅ completo |
| `extra_rumore_coerente/` | extra | Errore coerente vs Pauli (limite del modello Clifford-Pauli, cfr. Plaquette) | ✅ completo |

## Regola di validazione (dal documento del relatore)

Ogni risultato è accompagnato da **seed, numero di shot, modello di rumore e parametri**; le
figure si **rigenerano da script** (`../../figure_src/`), mai a mano. I file JSON sono la fonte
dei numeri riportati in tesi. Un grafico senza questi elementi non è un risultato scientifico.
