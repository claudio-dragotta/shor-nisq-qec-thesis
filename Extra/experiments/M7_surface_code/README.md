# M7 — Surface code (Stim + PyMatching) — ⬜ DA FARE

**Blocco M7** del documento di indirizzo (§10). Codice topologico scalabile per la stima del
**logical error rate** p_L con un decoder reale.

## Cosa conterrà

- `qec_surface.py` — costruzione del surface code (rotated memory X/Z) con **Stim**, decoding
  **MWPM** con **PyMatching**, curve p vs p_L per distanze d = 3, 5, 7.
- `results_M7_surface_*.json` — logical error rate per (d, p, base).

## Prerequisito ambiente

```bash
pip install stim pymatching     # oltre a quanto già in requirements.txt
```

## Cosa aspettarsi (flag)

- **Sanity** a p=0: p_L ≈ 0 per ogni d.
- **Flag decisivo**: le curve d=3,5,7 si **incrociano** a una soglia p_th ≈ 0.5–1%.
- Sotto soglia: d ↑ ⟹ p_L ↓ (soppressione esponenziale in d). Sopra soglia: d ↑ ⟹ p_L ↑.
- Statistica ≥ 10⁴ shot; partire da d=3, salire a d=5,7 solo se il decoding è sostenibile.

Dettagli e criteri in `../../../piano_azione_qec.md` (Parte V, sezione M7).
