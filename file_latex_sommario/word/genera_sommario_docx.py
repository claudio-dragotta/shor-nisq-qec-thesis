"""Genera il sommario in Word con la stessa impaginazione di main.tex.

Impaginazione ripresa da file_latex_sommario/main.tex:
  - A4, margini 3 cm sopra/sotto/destra, 3,5 cm a sinistra;
  - Times New Roman 12 pt, interlinea 1,15, nessun rientro, 3 pt fra i paragrafi;
  - intestazione con logo UCBM a sinistra e riga in corsivo a destra, filetto sotto;
  - numero di pagina centrato a piè di pagina;
  - blocco del titolo: titolo in grassetto centrato, tabella con laureando, relatore,
    correlatore e sessione, filetto;
  - sezioni numerate in grassetto 14 pt, sottosezioni in grassetto 12 pt;
  - bibliografia su due colonne in corpo 6,4 pt.

Il testo si scrive in CONTENUTO con un piccolo markup:
  [i]...[/i] corsivo (variabili matematiche), [sup]...[/sup] apice,
  [sub]...[/sub] pedice.

Uso:
    python genera_sommario_docx.py
"""
import os
import re

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

QUI = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(QUI, '..', 'figure', 'ucbm-logo.png')
USCITA = os.path.join(QUI, 'Sommario_Tesi_Dragotta.docx')

FONT = 'Times New Roman'
TITOLO = ('Shor’s Algorithm under Noise: Machine-Learning Ablation, '
          'Quantum Error Correction, and Approximate QFT')
INTESTAZIONE = ('Sommario del Lavoro di Tesi, Laurea Magistrale in Ingegneria dei '
                'Sistemi Intelligenti, Università Campus Bio-Medico di Roma')
BLOCCO = [('Laureando', 'Claudio Dragotta', 'Relatore', 'Prof. Paolo Soda'),
          ('Correlatore', 'Ing. Floriano Caprio', 'Sessione di Laurea',
           'Ottobre — A.A. 2025/2026')]

# ---------------------------------------------------------------------------
# Contenuto: (livello, titolo, [paragrafi]). Livello 1 = sezione, 2 = sottosezione.
# Le sezioni ancora da trascrivere hanno l'elenco dei paragrafi vuoto.
# ---------------------------------------------------------------------------
CONTENUTO = [
    (1, 'Introduzione e obiettivi', [
        'L’algoritmo di Shor consente di fattorizzare numeri interi in tempo polinomiale '
        'rispetto alla lunghezza binaria dell’input, con implicazioni per la sicurezza dei '
        'sistemi crittografici fondati sulla difficoltà della fattorizzazione [1–3]. '
        'La realizzazione di questo vantaggio teorico richiede tuttavia un controllo degli '
        'errori compatibile con la profondità dei circuiti. Errori nelle operazioni, '
        'decoerenza e lettura imperfetta possono alterare la distribuzione delle misure e '
        'compromettere l’informazione necessaria alla ricerca dell’ordine '
        'moltiplicativo [4].',
        'La tesi sviluppa uno studio simulativo volto a stabilire quali interventi migliorino '
        'effettivamente l’affidabilità della computazione e rispetto a quali riferimenti. '
        'Il percorso comprende due fasi principali: la valutazione del post-processing classico '
        'degli esiti di Shor, con uno studio di ablazione del contributo del machine learning; '
        'la caratterizzazione di codici di correzione quantistica e decoder delle sindromi. '
        'Completano il lavoro un’analisi separata della sensibilità di Shor agli errori '
        'di porta e una campagna sull’ottimizzazione circuitale mediante trasformata di '
        'Fourier quantistica approssimata, o AQFT.',
        'Gli ambiti di intervento — selezione degli esiti, protezione dell’informazione '
        'e riduzione del costo circuitale — sono collegati da un criterio comune: confrontare '
        'ogni soluzione con un riferimento esplicito, isolare il contributo dei singoli '
        'componenti e misurare il beneficio mediante indicatori coerenti con il compito. Le '
        'campagne sperimentali sono state condotte separatamente, difatti i metodi di correzione '
        'degli errori non sono stati applicati direttamente all’intero circuito di Shor in '
        'un’unica simulazione.',
    ]),
    (1, 'Materiali e metodi', []),
    (2, 'Algoritmo di Shor, validazione e definizione del successo', [
        'Scelta una base [i]a[/i] coprima con il numero [i]N[/i] da fattorizzare, la successione '
        '[i]a[/i][sup][i]x[/i][/sup] mod [i]N[/i] è periodica; il periodo, detto ordine '
        '[i]r[/i], è il minimo intero positivo per cui [i]a[/i][sup][i]r[/i][/sup] ≡ 1 '
        '(mod [i]N[/i]). La parte quantistica lo stima con stima di fase e QFT inversa; la parte '
        'classica ricava i fattori per approssimazione razionale e massimo comune divisore, e li '
        'verifica.',
        'L’istanza principale è [i]N[/i] = 15, [i]a[/i] = 7, con otto qubit di controllo '
        'e quattro di lavoro; l’ordine è [i]r[/i] = 4 e gli esiti ideali del registro di '
        'controllo sono 0, 64, 128 e 192. Ogni esecuzione con misura, detta [i]shot[/i], '
        'restituisce un solo esito; molti shot formano l’istogramma su cui opera il '
        'post-processing. Il successo è il recupero di fattori non banali, non la '
        'ricostruzione esatta dell’ordine. Vi conducono tre dei quattro picchi ideali, con '
        'probabilità complessiva del 75%. La verifica classica è però permissiva e '
        'accetta 63 dei 256 valori, tanto che esiti del tutto uniformi darebbero comunque un '
        'successo di 63/256 ≃ 24,61%. Questo riferimento dipende dall’istanza e dal '
        'post-processing e non misura la fedeltà dello stato quantistico. Mostra inoltre che '
        'fattorizzazioni corrette possono essere ottenute anche quando la distribuzione degli '
        'esiti di misura del registro di controllo ha perso gran parte della struttura ideale '
        'dei picchi [5].',
        'La correttezza dei circuiti è verificata indipendentemente dal successo della '
        'fattorizzazione, controllando operatori modulari, ripristino dei qubit ausiliari e '
        'accordo con le distribuzioni teoriche. Oltre a [i]N[/i] = 15, si considerano le istanze '
        '[i]N[/i] = 21, [i]a[/i] = 2 e [i]N[/i] = 35, [i]a[/i] = 6, che, validate idealmente, '
        'usano l’aritmetica reversibile di Beauregard [6]; solo [i]N[/i] = 21 entra nelle '
        'prove rumorose esplorative sull’AQFT, perché per [i]N[/i] = 35 le risorse '
        'hardware disponibili non consentivano la simulazione di un circuito di Shor adeguato. '
        'Si impiegano Qiskit/Aer, scikit-learn, Stim e PyMatching, registrando versioni, '
        'parametri, semi casuali e identificativi dei circuiti.',
    ]),
    (2, 'Sensibilità di Shor agli errori di porta', [
        'Il punto di partenza dello studio è stato capire quanto l’algoritmo di Shor '
        'sia robusto agli errori di porta. Nel circuito dell’istanza principale, compilato '
        'nelle porte native RZ, SX, X e CX (profondità 412, con 224 porte CX e 70 porte SX), '
        'si introducono in simulazione errori di Pauli indipendenti dopo ogni porta compilata; '
        'le rotazioni RZ, che sono virtuali, ne sono escluse. L’intensità del rumore '
        'è controllata da un unico parametro, la probabilità [i]p[/i][sub]g[/sub] che '
        'dopo una porta si verifichi un errore di Pauli diverso dall’identità, fatta '
        'variare su 13 valori fra 0 e 0,5.',
        'Per ciascun valore si eseguono 20 repliche indipendenti da 4.096 shot e si misura il '
        'successo per singolo shot, cioè la frazione di esiti da cui il post-processing '
        'ricava i fattori. Senza errori il successo è del 74,89% (intervallo di confidenza '
        'al 95% [74,59%; 75,18%]), in accordo con il 75% atteso. Già errori piccoli lo '
        'riducono in modo visibile: 72,5% per [i]p[/i][sub]g[/sub] = 0,1%, 56,5% per '
        '[i]p[/i][sub]g[/sub] = 1%, 45,2% per [i]p[/i][sub]g[/sub] = 2% e 29,5% per '
        '[i]p[/i][sub]g[/sub] = 5%. Da [i]p[/i][sub]g[/sub] = 10% in poi il successo resta '
        'intorno al 25% e per [i]p[/i][sub]g[/sub] = 0,5 vale il 24,59%, praticamente il '
        'riferimento uniforme del 24,61%.',
        'La fragilità dipende dal numero di porte: con 294 porte soggette a errore, già '
        'per [i]p[/i][sub]g[/sub] = 1% si verificano in media circa tre errori per esecuzione. '
        'Questo risultato è la premessa del lavoro e motiva le tre strategie successive: '
        'selezionare meglio gli esiti già misurati, proteggere l’informazione con la '
        'correzione quantistica degli errori e ridurre il numero di porte su cui il rumore può '
        'agire. Mostra inoltre che il solo numero di fattorizzazioni corrette non basta a '
        'descrivere quanta struttura quantistica rimanga nel circuito.',
        'Il modello è fenomenologico e uniforme, non una calibrazione di hardware reale: '
        '[i]p[/i][sub]g[/sub] è una probabilità di errore per porta e non è '
        'direttamente confrontabile con la probabilità di fallimento logico '
        '[i]p[/i][sub]L[/sub] dei codici di correzione, poiché Shor non viene eseguito con '
        'una compilazione fault-tolerant completa.',
    ]),
    (2, 'Mitigazione degli errori mediante post-processing e machine learning', [
        'La prima strategia agisce a valle della misura: senza modificare il circuito, cerca di '
        'ricavare i fattori dagli esiti rumorosi scegliendo meglio quali verificare, e valuta '
        'se un modello di machine learning renda questa scelta più efficace. Tre strategie '
        'di selezione, con estrattore dei fattori e regola dei pareggi comuni, operano sugli '
        'stessi istogrammi, uno per iterazione quantistica, da 1.024 shot ciascuno. TOP-1 '
        '(Metodo 1) verifica il solo esito più frequente; TOP-4 fino a quattro candidati '
        'ordinati per frequenza; il Metodo 2 applica TOP-4 solo se un classificatore predice il '
        'successo del candidato dominante. Il confronto fra Metodo 2 e TOP-4 senza filtro è '
        'lo studio di ablazione, che stabilisce se il vantaggio venga dal modello appreso o dal '
        'semplice provare più candidati.',
        'Due scenari illustrativi, UC1 di riferimento e UC2 di stress, includono '
        'depolarizzazione, rilassamento termico ed errori di lettura; per ciascuno scenario, '
        '2.000 istogrammi con parametri variati entro ±50% del nominale sono divisi '
        '60%/20%/20% fra addestramento, selezione e verifica. Random forest, support vector '
        'machine (SVM) e perceptron multistrato sono confrontati su F1; il modello scelto è '
        'valutato su 400 istogrammi indipendenti per scenario. La metrica primaria è il '
        'numero di iterazioni per ottenere i fattori; l’accuratezza è stata considerata '
        'un elemento secondario nello studio del classificatore, mentre il tempo di calcolo '
        'è stato rapportato alle risorse hardware disponibili. Si usano 30 repliche appaiate '
        'per scenario e al massimo 50 iterazioni.',
    ]),
    # Numerazione dei riferimenti in ordine di prima citazione: con questo ordine dei
    # paragrafi AlphaQubit diventa [10], Bravyi et al. [11], Roffe et al. [12].
    (2, 'Correzione quantistica degli errori: surface code e codici qLDPC', [
        'La seconda strategia protegge l’informazione prima che il rumore la distrugga. '
        'Nella correzione quantistica degli errori, l’informazione di un qubit logico viene '
        'distribuita su più qubit fisici; le sindromi permettono di rilevare gli errori '
        'senza misurare direttamente lo stato logico e guidano il decoder nella scelta della '
        'correzione. Le prestazioni sono misurate attraverso la probabilità di fallimento '
        'logico [i]p[/i][sub]L[/sub].',
        'Codice a ripetizione e codice di Steane sono utilizzati come verifiche preliminari, '
        'mentre l’analisi principale riguarda circuiti di memoria basati su surface code '
        '[7–9], con errori nelle operazioni, nella preparazione e nella misura e, in alcune '
        'configurazioni, crosstalk tra qubit adiacenti. Il decoder di riferimento è il '
        '[i]minimum-weight perfect matching[/i] (MWPM), che associa a coppie le sindromi '
        'attivate scegliendo la configurazione di errori più probabile. MWPM è '
        'confrontato con una rete neurale autonoma e con una strategia ibrida, la cui soglia '
        'd’intervento è selezionata sul validation set e mantenuta fissa sul test '
        'set [10].',
        'Uno studio esplorativo confronta inoltre il surface code con il Gross code di IBM, un '
        'codice quantum Low-Density Parity-Check (qLDPC) che codifica 12 qubit logici in 144 '
        'qubit di dato [11], nel modello code-capacity, con errori sui soli qubit di dato e '
        'sindromi perfette. BP+OSD ([i]belief propagation with ordered statistics '
        'decoding[/i]) è usato come ulteriore decoder di confronto sul surface code e come '
        'decoder del Gross code [12].',
    ]),
    (2, 'Riduzione del rumore con la AQFT', []),
    (1, 'Risultati', []),
    (2, 'Validazione dei circuiti', []),
    (2, 'Post-processing e machine learning', []),
    (2, 'Correzione quantistica degli errori', []),
    (2, 'Riduzione del rumore con la AQFT', []),
    (1, 'Discussione e conclusioni', []),
    (1, 'Riferimenti bibliografici essenziali', []),
]

# Riferimenti, nell'ordine di prima citazione; si stampano quando la sezione
# della bibliografia verra' trascritta.
BIBLIOGRAFIA = []


# ---------------------------------------------------------------------------
# Utilita' di formattazione
# ---------------------------------------------------------------------------
def _font(run, size=12, bold=False, italic=False):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.insert(0, rfonts)
    for attr in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
        rfonts.set(qn(attr), FONT)


def _spaziatura(par, prima=0, dopo=3, interlinea=1.15):
    pf = par.paragraph_format
    pf.space_before = Pt(prima)
    pf.space_after = Pt(dopo)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = interlinea
    pf.first_line_indent = Cm(0)


def _bordo_sotto(elemento_pr, spessore_ottavi=4):
    """Filetto inferiore (spessore in ottavi di punto: 4 = 0,5 pt)."""
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), str(spessore_ottavi))
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '000000')
    pbdr.append(bottom)
    elemento_pr.append(pbdr)


def _spazi_indivisibili(testo):
    """Evita che formule e citazioni si spezzino a fine riga, come il ~ di LaTeX."""
    testo = testo.replace(' = ', ' = ').replace(' ≡ ', ' ≡ ')
    testo = testo.replace(' \u2243 ', '\u00a0\u2243\u00a0').replace('mod ', 'mod\u00a0')
    testo = re.sub(r'(Metodo|Sezione) (\d)', '\\1\u00a0\\2', testo)
    return re.sub(r' \[(\d)', ' [\\1', testo)


def _senza_sillabazione(par):
    ppr = par._p.get_or_add_pPr()
    e = OxmlElement('w:suppressAutoHyphens')
    ppr.append(e)


def testo_con_markup(par, testo, size=12, bold=False):
    """Scrive il testo interpretando [i], [sup], [sub]."""
    testo = _spazi_indivisibili(testo)
    stato = {'i': False, 'sup': False, 'sub': False}
    for pezzo in re.split(r'(\[/?(?:i|sup|sub)\])', testo):
        m = re.fullmatch(r'\[(/?)(i|sup|sub)\]', pezzo)
        if m:
            stato[m.group(2)] = not m.group(1)
            continue
        if not pezzo:
            continue
        run = par.add_run(pezzo)
        _font(run, size=size, bold=bold, italic=stato['i'])
        if stato['sup']:
            run.font.superscript = True
        if stato['sub']:
            run.font.subscript = True


def _senza_bordi(tabella):
    tblpr = tabella._tbl.tblPr
    bordi = OxmlElement('w:tblBorders')
    for lato in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        e = OxmlElement(f'w:{lato}')
        e.set(qn('w:val'), 'nil')
        bordi.append(e)
    tblpr.append(bordi)


def _margini_cella_zero(tabella):
    tblpr = tabella._tbl.tblPr
    mar = OxmlElement('w:tblCellMar')
    for lato in ('top', 'left', 'bottom', 'right'):
        e = OxmlElement(f'w:{lato}')
        e.set(qn('w:w'), '0')
        e.set(qn('w:type'), 'dxa')
        mar.append(e)
    tblpr.append(mar)


def _larghezze(tabella, cm):
    tabella.autofit = False
    for riga in tabella.rows:
        for cella, w in zip(riga.cells, cm):
            cella.width = Cm(w)


def _campo_pagina(par):
    """Inserisce il campo PAGE."""
    for tipo, testo in (('begin', None), (None, 'PAGE'), ('end', None)):
        run = par.add_run()
        _font(run, size=10)
        if tipo:
            fc = OxmlElement('w:fldChar')
            fc.set(qn('w:fldCharType'), tipo)
            run._element.append(fc)
        else:
            it = OxmlElement('w:instrText')
            it.set(qn('xml:space'), 'preserve')
            it.text = testo
            run._element.append(it)


# ---------------------------------------------------------------------------
# Impaginazione
# ---------------------------------------------------------------------------
def imposta_pagina(sezione):
    sezione.page_width, sezione.page_height = Cm(21.0), Cm(29.7)
    sezione.top_margin = Cm(3)
    sezione.bottom_margin = Cm(3)
    sezione.left_margin = Cm(3.5)
    sezione.right_margin = Cm(3)
    # in main.tex: head 1,35 cm + headsep 0,45 cm sopra il corpo del testo
    sezione.header_distance = Cm(1.2)
    sezione.footer_distance = Cm(1.6)


def intestazione(sezione, testo_destra):
    header = sezione.header
    header.is_linked_to_previous = False
    par0 = header.paragraphs[0]
    tab = header.add_table(rows=1, cols=2, width=Cm(16.5))
    _senza_bordi(tab)
    _margini_cella_zero(tab)
    _larghezze(tab, [5.5, 11.0])
    sx, dx = tab.rows[0].cells
    p = sx.paragraphs[0]
    _spaziatura(p, dopo=0, interlinea=1.0)
    p.add_run().add_picture(LOGO, height=Cm(1.02))
    p = dx.paragraphs[0]
    _spaziatura(p, dopo=0, interlinea=1.0)
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run(testo_destra)
    _font(run, size=10, italic=True)
    # cella destra centrata in verticale, come \parbox[c]
    tcpr = dx._tc.get_or_add_tcPr()
    va = OxmlElement('w:vAlign')
    va.set(qn('w:val'), 'center')
    tcpr.append(va)
    # il paragrafo vuoto iniziale dell'intestazione porta il filetto sotto la tabella
    par0._p.addnext(tab._tbl)
    header._element.append(par0._p)
    _spaziatura(par0, dopo=0, interlinea=1.0)
    _bordo_sotto(par0._p.get_or_add_pPr(), spessore_ottavi=3)
    run = par0.add_run()
    _font(run, size=2)


def pie_di_pagina(sezione):
    footer = sezione.footer
    footer.is_linked_to_previous = False
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _campo_pagina(p)


def blocco_titolo(doc):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _spaziatura(p, prima=0, dopo=6)
    _senza_sillabazione(p)
    _font(p.add_run(TITOLO), size=14, bold=True)

    tab = doc.add_table(rows=2, cols=2)
    _senza_bordi(tab)
    _margini_cella_zero(tab)
    _larghezze(tab, [7.6, 8.9])
    tab.alignment = WD_TABLE_ALIGNMENT.LEFT
    for r, (e1, v1, e2, v2) in enumerate(BLOCCO):
        for c, (etichetta, valore) in enumerate(((e1, v1), (e2, v2))):
            cp = tab.rows[r].cells[c].paragraphs[0]
            _spaziatura(cp, dopo=1, interlinea=1.0)
            _font(cp.add_run(f'{etichetta}: '), size=11, bold=True)
            _font(cp.add_run(valore), size=11)

    p = doc.add_paragraph()
    _spaziatura(p, prima=0, dopo=2, interlinea=1.0)
    _bordo_sotto(p._p.get_or_add_pPr(), spessore_ottavi=3)
    _font(p.add_run(), size=4)


def titolo(doc, numero, testo, livello):
    p = doc.add_paragraph()
    if livello == 1:
        _spaziatura(p, prima=9, dopo=2)
        size = 14
    else:
        _spaziatura(p, prima=6, dopo=1)
        size = 12
    p.paragraph_format.keep_with_next = True
    _senza_sillabazione(p)
    _font(p.add_run(f'{numero} {testo}'), size=size, bold=True)


def paragrafo(doc, testo):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    _spaziatura(p)
    testo_con_markup(p, testo)


def colonne(sezione, n, spazio_pt=10):
    sectpr = sezione._sectPr
    cols = sectpr.find(qn('w:cols'))
    if cols is None:
        cols = OxmlElement('w:cols')
        sectpr.append(cols)
    cols.set(qn('w:num'), str(n))
    cols.set(qn('w:space'), str(int(spazio_pt * 20)))


def main():
    doc = Document()
    stile = doc.styles['Normal']
    stile.font.name = FONT
    stile.font.size = Pt(12)
    stile.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
    # lingua italiana e sillabazione automatica, come la sillabazione di LaTeX:
    # senza, il testo giustificato lascia spazi larghi fra le parole
    lang = OxmlElement('w:lang')
    lang.set(qn('w:val'), 'it-IT')
    stile.element.rPr.append(lang)
    impostazioni = doc.settings.element
    sill = OxmlElement('w:autoHyphenation')
    sill.set(qn('w:val'), 'true')
    impostazioni.append(sill)

    sezione = doc.sections[0]
    imposta_pagina(sezione)
    intestazione(sezione, INTESTAZIONE)
    pie_di_pagina(sezione)

    blocco_titolo(doc)

    n1 = n2 = 0
    for livello, testo_titolo, paragrafi in CONTENUTO:
        if livello == 1:
            n1 += 1
            n2 = 0
            numero = str(n1)
        else:
            n2 += 1
            numero = f'{n1}.{n2}'
        if testo_titolo.startswith('Riferimenti') and BIBLIOGRAFIA:
            titolo(doc, numero, testo_titolo, livello)
            sez = doc.add_section(WD_SECTION.CONTINUOUS)
            colonne(sez, 2)
            for i, voce in enumerate(BIBLIOGRAFIA, 1):
                p = doc.add_paragraph()
                _spaziatura(p, dopo=0, interlinea=1.0)
                p.paragraph_format.left_indent = Cm(0.45)
                p.paragraph_format.first_line_indent = Cm(-0.45)
                testo_con_markup(p, f'[{i}] {voce}', size=6.4)
            continue
        titolo(doc, numero, testo_titolo, livello)
        for t in paragrafi:
            paragrafo(doc, t)

    doc.save(USCITA)
    print(f'Salvato: {USCITA}')


if __name__ == '__main__':
    main()
