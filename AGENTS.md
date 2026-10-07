# Compilazione LaTeX

Non creare file ausiliari di compilazione nelle cartelle del progetto.
Usare `scripts/compila_tesi.ps1 -Source file_latex_v2/main_relatore.tex`
(oppure main.tex, o il sorgente del sommario). Lo script compila nella
cartella temporanea di Windows e copia soltanto il PDF finale accanto al sorgente.
Anche log, render e verifiche temporanee devono stare fuori dal progetto.
Conservare sorgenti .tex, bibliografie .bib e immagini necessarie alla compilazione.
