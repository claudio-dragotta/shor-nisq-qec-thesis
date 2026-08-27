# Campagna riproducibile v2 — 2026-08-19

Questa directory contiene esclusivamente artefatti rigenerati dopo:

- correzione del moltiplicatore controllato `7*x mod 15`;
- compilazione deterministica nella base `rz/sx/x/cx`;
- trattamento di `rz` come gate virtuale privo di rumore e durata;
- applicazione dei canali 1Q a `sx/x` e dei canali 2Q a `cx`;
- distinzione esplicita tra successo all'ultima iterazione e fallimento;
- ranking con tie-break SHA-256 seeded e indipendente dall'ordine dei dizionari;
- riuso dello stesso istogramma per i confronti appaiati TOP-1/TOP-K;
- salvataggio di revisione, hash del circuito e versioni software.

Gli artefatti nella directory padre restano conservati come storico, ma non sono
confrontabili direttamente con questa revisione.

Sottodirectory previste:

- `training/top1`: modelli destinati all'ablazione M2;
- `training/top16`: audit della regola documentata (può produrre classe unica);
- `training/checkpoints`: dataset parziali atomici, riusabili solo a contratto identico;
- `results`: baseline, sweep e confronto ZNE;
- `figures`: figure generate esclusivamente dagli artefatti v2;
- `logs`: stdout/stderr e tempi delle esecuzioni canoniche.

Lo sweep parametrico salva inoltre un checkpoint v4 dopo ogni famiglia completa; il file
finale e il checkpoint condividono lo stesso manifest e non vanno mescolati con gli smoke v3.

Ambiente canonico: Ubuntu 24.04 su WSL2, Python 3.12, dipendenze esatte in
`Extra/experiments/requirements.txt`.
