# DESIGN.md — Wallet

Design system di Wallet, prodotto con Claude Design. Questo file è la fonte di verità per
palette, tipografia, forme, iconografia e tono di voce che `CLAUDE.md` dichiarava "da
produrre". I token vanno travasati in `frontend/src/styles/tokens.css` (blocco `@theme` di
Tailwind 4); nei componenti solo classi Tailwind, nessun valore arbitrario.

## Direzione

**Cruscotto notturno.** Scuro, calmo, denso di numeri; un solo colore che brilla. Tema solo
scuro in V1. Nessuna immagine, nessun pattern: il prodotto è fatto di numeri, testo e
grafici.

## Colori

Base (tema scuro, verde-tinto):

| Token | Valore | Uso |
|---|---|---|
| `--bg-app` | `#060A08` | fondo pagina |
| `--bg-raise` | `#0A100D` | fogli, sheet |
| `--surface-card` | `#0E1613` | card |
| `--surface-card-2` | `#131D18` | superfici annidate, input chip |
| `--surface-input` | `#0B1210` | campi di input |
| `--border-soft` | `rgba(126,255,192,.08)` | bordo card, divisori |
| `--border-strong` | `rgba(126,255,192,.16)` | bordo controlli |
| `--border-focus` | `rgba(61,242,155,.55)` | focus |

Testo: `--ink-1 #EDF5F0` (primario), `--ink-2 #9FB4AA` (secondario), `--ink-3 #5C6F65`
(terziario), `--ink-on-accent #04130B` (su accento).

Accento (uno solo): `--accent #3DF29B`, hover `#63F6B0`, press `#28D584`, velature
`--accent-dim rgba(61,242,155,.12)` e `--accent-dim-2 (.22)`.

Semantici del denaro:

| Token | Valore | Regola |
|---|---|---|
| `--money-income` | `#3DF29B` | entrate, segno `+` |
| `--money-expense` | `#FF6B5E` | uscite, segno `−` |
| `--money-transfer` | `#6FCDF2` | **mai verde, mai rosso, senza segno** |
| `--money-adjustment` | `#C9B458` | rettifiche da riconciliazione |

Stati: `--danger #FF6B5E` (+ `--danger-dim`), `--warn #FFC85C`, `--ok #3DF29B`.
Superfici di stato: `--surface-selected rgba(61,242,155,.10)`, `--surface-hover
rgba(237,245,240,.04)`, `--scrim rgba(3,6,5,.72)`.

Serie dei grafici (Recharts si ridisegna SOLO su questi): `--chart-1 #3DF29B`,
`--chart-2 #6FCDF2`, `--chart-3 #B18CFF`, `--chart-4 #FFC85C`, `--chart-5 #FF7BA8`,
`--chart-6 #79E6D0`; griglia `--chart-grid rgba(126,255,192,.07)`, assi `--chart-axis
#5C6F65`.

⚠️ **Esteso a M3: quattro colori in più per le categorie** — `--chart-7 #7FB0FF`,
`--chart-8 #FF9E64`, `--chart-9 #D6E45C`, `--chart-10 #E86FD0`. Sei bastano a un grafico e
non bastano a un elenco di categorie, che di categorie ne ha una dozzina e le deve far
distinguere a colpo d'occhio. **I grafici continuano a usare solo le prime sei**: oltre,
le linee smettono di essere leggibili, e una torta con troppe fette raggruppa la coda in
"Altro" invece di inventarsi tinte. Le tonalità sono distanti fra loro di proposito —
nessuna è una sfumatura della vicina.

## Tipografia

- **Space Grotesk** (400–700) — display e **tutti i numeri**, sempre con
  `font-feature-settings: "tnum" 1, "lnum" 1`: gli importi si leggono in colonna.
- **Instrument Sans** (400–600) — testo.
- ⚠️ Sostituzione da confermare: nessun file di font fornito → Google Fonts.

Scala mobile-first:

| Token | px | Uso |
|---|---|---|
| hero | 34/40, num 600 | patrimonio, saldo grande |
| title | 22/28, display 600 | titolo di sezione |
| heading | 17/24, display 600 | titolo di card |
| body | 15/22, 400 | testo |
| caption | 13/18, 400 | sottotitoli, meta |
| micro | 11/14, maiuscolo, tracking .06em | etichette, assi |

## Il denaro a schermo

- Formato: `1.234,56 €` — virgola decimale, punto migliaia, euro dopo con spazio.
- Tabulare, allineato a destra, sempre nella stessa posizione.
- Segno esplicito: `+` entrate (verde), `−` uscite (rosso); trasferimenti ciano **senza
  segno**; totali e saldi senza segno.
- La parola "centesimi" non arriva mai all'utente; la divisione per 100 vive solo nel
  formattatore (componente `Amount` / `formatMoney`).

## Forme, spaziatura, elevazione

- Spaziatura: 4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48. Gap fra card 12. Target tattile
  minimo 44px. Tab bar 64, FAB 56.
- ⚠️ **I margini si stringono sul telefono, non sul desktop.** Margine pagina **12** da
  mobile e 32 da `sm`; padding card **16** da mobile e 20 da `sm`. Venti ovunque stava bene
  in un mock da desktop e su 390px mangiava un decimo della larghezza: fra margine pagina,
  bordo della card e padding della riga, il nome di un movimento cominciava a 32 px dal
  bordo e veniva troncato con dello spazio vuoto accanto. Sul desktop la larghezza non è
  scarsa e i margini restano larghi.
- Raggi: card 16, controlli 12, chip/pillole 999, sheet 24 in alto.
- Card: `--surface-card` + bordo 1px `--border-soft` + `--shadow-card` (ombra profonda +
  filo interno chiaro). Mai bordi colorati solo a sinistra.
- Glow verde (`--glow-accent`): riservato ad azione primaria e FAB. Non si spalma.
- Trasparenza e blur: solo scrim e tab bar (blur 12px). Non sulle card.

## Movimento e stati

- Durate 120/200ms, `cubic-bezier(.2,.8,.2,1)`. Fade e slide dei fogli dal basso. Niente
  bounce, niente parallax.
- Hover: `--surface-hover` (sull'accento: `--accent-hover`). Press: accento più scuro +
  `scale(.98)`. Focus: `--border-focus` + anello `--accent-dim`.
- BusyOverlay solo oltre i 200ms; il salvataggio di un movimento non è ottimistico.

## Iconografia e marchio

- **Lucide** (stroke 2px), 20–24px, colore `--ink-2`, attive `--accent` — sostituzione
  dichiarata, nessun set fornito. In produzione `lucide-react`.
- **Le icone delle categorie sono un insieme curato di 56**, non le 1500 di Lucide: 1500
  non è una scelta, è un problema di ricerca. Nel selettore stanno **otto per volta in
  pagine a tema** (Casa, Spesa e cibo, Trasporti, Salute e cura, Svago, Soldi e lavoro,
  Altro) con le frecce per scorrerle: il nome del gruppo dice dove sei, che è più utile di
  "pagina 3 di 7".
- Trasferimenti: `arrow-left-right`, icona in contenitore **quadrato** (raggio 12); le
  categorie in contenitore rotondo.
- Niente emoji, niente unicode come icone, niente SVG disegnati a mano.
- **Nessun logo**: wordmark tipografico "Wallet." in Space Grotesk 600, punto finale in
  `--accent`.

## I grafici (M4)

- **La cornice è un componente**, `charts/ChartFrame`: titolo, una nota a destra, e **il
  caso vuoto**. ⚠️ Il vuoto vive lì e non in sette posti: un grafico con gli assi a zero si
  legge come "hai speso zero", che è un'altra affermazione, e sette componenti che ci
  provano ognuno per conto suo sbagliano prima o poi.
- **Il tooltip è scritto, non ristilizzato.** Quello di Recharts è un rettangolo bianco con
  un bordo; passargli `contentStyle` significa scrivere in linea cose che i token dicono
  già. `charts/MoneyTooltip` è una card come le altre, e gli importi passano da
  `formatMoney`.
- **Assi senza linea e senza tacche**, etichette 11px in `--chart-axis`, griglia solo
  orizzontale in `--chart-grid`. `lib/chart.ts` è **l'unico posto del frontend che nomina un
  colore per un grafico**.
- ⚠️ **Le uscite per categoria non sono un grafico di libreria, sono un elenco con dentro
  una barra.** Ogni riga porta nome, importo, quota e variazione, e deve restare leggibile a
  390px: Recharts qui sarebbe una libreria combattuta, e la prima cosa che troncherebbe
  sono le etichette.
- ⚠️ **Entrate e uscite divergono da uno zero: un mese è una colonna sola.** Prima erano due
  barre affiancate, ed era il disegno sbagliato — con una coppia per mese e dodici mesi a
  schermo, niente ti dice se la barra rossa che stai guardando appartiene alla verde alla
  sua sinistra o a quella alla sua destra. Leggerlo voleva dire contare. Sopra e sotto uno
  zero condiviso lo risolve nella struttura invece che con un'etichetta, ed è anche la
  codifica più onesta: entrate e uscite sono opposte di senso, non due grandezze della
  stessa cosa. Quello che avanza sull'asse **è** il risparmio del mese.
  ⚠️ L'asse mostra entrambe le metà come numeri positivi: il lato porta già il segno, e
  scriverlo due volte sarebbe rumore.
- ⚠️ **La legenda si scrive, non si eredita.** Tre colori senza chiave è un grafico che va
  spiegato; quella di Recharts arriva con tipo, spaziature e forme sue, e ristilizzarla
  costa più che dirla a mano.
- ⚠️ **La torta è un anello, sei fette e poi "Altro".** Il buco al centro tiene il totale,
  che è il numero di cui le fette sono una proporzione: scriverlo fuori dal grafico
  obbligherebbe a guardare in due posti. Oltre le sei fette la coda si raggruppa, che è la
  regola già scritta qui — non ci si inventano tinte.
  ⚠️ Ogni fetta però prende **il colore della sua categoria**, anche quando è il settimo o
  il decimo della palette, ed è una lettura deliberata della regola "i grafici usano solo le
  prime sei serie": quella regola esiste perché i colori distinguibili finiscono, e usare il
  colore che quella categoria ha già nell'icona e nell'elenco è più leggibile, non meno. Due
  categorie possono avere lo stesso colore, ed è per questo che **l'elenco sotto è la
  legenda** — anello e barre stanno nella stessa cornice, non in due card che dicono la
  stessa cosa due volte.
- ⚠️ **La variazione rispetto al periodo prima è in inchiostro neutro**, non rossa né verde.
  Spendere 120 € in più in trasporti è un fatto; se sia una brutta notizia non lo decide
  l'app.
- ⚠️ **Ogni numero si apre.** Una fetta, una barra di un mese, un totale portano all'elenco
  dei movimenti **con i filtri nell'URL** — stesso periodo, stessa categoria da cui il
  numero è nato. Perciò i filtri di Movimenti vivono nella query string e non nello stato
  del componente: è ciò che rende la risposta a "e da dove esce?" una pagina che si può
  anche ricaricare e da cui si torna indietro.
- **Il patrimonio non parte da zero** sull'asse: quel grafico risponde a "sta salendo?", e
  una scala da zero appiattirebbe un anno di risparmio in una riga dritta. È l'unico posto
  in cui la forma conta più della grandezza — ogni altro numero è mostrato intero, in euro.

## L'obiettivo di risparmio (M4)

- ⚠️ **Il verdetto è una parola, non una barra**: "Obiettivo raggiunto" in verde o
  "Obiettivo mancato" in rosso, sul ciclo che un nuovo stipendio ha già chiuso. Una barra
  su una tratta finita non dice niente di più di una parola, e occupa dieci volte lo
  spazio.
- ⚠️ **Il numero grande è quanto puoi ancora spendere**, non quanto hai risparmiato: è
  l'unico numero della schermata su cui puoi ancora agire. Taglia `hero`, e sotto la barra
  si riempie con lo speso rispetto allo spendibile (stipendio meno obiettivo) — quindi
  "piena" vuol dire "sei alla riga", non "bravo".
- ⚠️ **Tre stati vuoti diversi, tre frasi diverse**: manca l'obiettivo, manca la categoria
  dello stipendio, manca il secondo stipendio. Una barra a zero sarebbe la stessa immagine
  per tutti e tre e vera per nessuno.

## L'app installata (M5)

- **L'icona è una banconota** — la `Banknote` di Lucide, verde accento su `--bg-app`. Non è
  un logo e non ne inventa uno: è l'icona che l'app già usa, ingrandita. ⚠️ Non un simbolo
  del dollaro: la V1 è **solo euro**, quindi il `$` sarebbe l'unico simbolo sbagliato da
  metterci; una banconota dice "soldi" senza scegliere una valuta.
- ⚠️ **La versione mascherata sta più stretta.** Android ritaglia l'icona con una forma sua
  e solo l'80% centrale è garantito: il glifo dell'icona `maskable` è più piccolo, o gli
  angoli della banconota si perdono.
- **La fascia offline è ocra** (`--warn`, la stessa famiglia delle rettifiche), non rossa:
  non è un errore, è uno stato. ⚠️ E dice **cosa comporta per te** — "quello che registri
  adesso non viene salvato" — non solo che la rete manca. Senza la seconda metà della frase
  uno scopre da solo, a fine mese, che la spesa non era stata salvata.
- ⚠️ **Non offre di salvare per dopo.** L'inserimento offline è stato valutato e scartato
  per la V1; prometterlo qui sarebbe una bugia detta dall'interfaccia.

## Tono di voce

Italiano, sentence case, seconda persona informale, niente emoji. Descrive, non
prescrive. Un periodo senza dati si dice a parole ("Nessun movimento in questo periodo"),
mai un grafico a zero. Etichette oneste ("proiezione lineare", non "previsione").

## Layout e navigazione

- Mobile-first, riferimento 390px.
- ⚠️ **Rivisto in M2. Cinque sezioni, e il profilo non è una di quelle**: Riepilogo,
  Movimenti, Conti, **Categorie**, Analisi. Le categorie hanno smesso di stare dentro Conti
  dietro un selettore e si sono prese una sezione loro.
- Tab bar fissa in basso con le cinque sezioni, **solo icone a 26px, senza etichette**:
  cinque parole su 390px affollano la riga e vengono troncate lo stesso, le sezioni si
  imparano al primo uso, e il nome resta per chi usa uno screen reader.
- **Il profilo sta in alto a destra su telefono**, in una testata fissa insieme al
  wordmark: è dove si cerca "io", ed è ciò che restituisce la quinta scheda alle categorie.
  **Su desktop sta invece in fondo alla sidebar**, che di voci ne regge sei senza sforzo.
  ⚠️ Una strada sola per schermata, per piattaforma: mai il bottone in alto *e* la voce in
  sidebar insieme.
- ⚠️ **Il bottone + non è una scheda.** Il disegno originale lo metteva al centro di una
  barra da quattro; con cinque il centro non esiste più, quindi fluttua in basso a destra
  sopra la barra. Il principio non cambia — l'inserimento è l'unica azione con un posto
  fisso sullo schermo — cambia dove quel posto sta.
- L'elenco dei soldi si legge in colonna: importo a destra, riga movimento con icona,
  titolo, sottotitolo `categoria · conto` (troncato con ellissi, mai a capo).
- ⚠️ **La data non sta nella riga, sta nell'intestazione del giorno.** L'elenco è
  raggruppato per giornata — `Oggi`, `Ieri`, poi `giovedì 12 marzo` — con a destra il
  totale **delle sole uscite** di quel giorno. Ripetere la stessa data su sei righe di fila
  è rumore; e sommare trasferimenti o rettifiche in quel totale farebbe sembrare peggiore
  una giornata proprio nel numero che si guarda di sfuggita.
- ⚠️ **Una card per giorno, con l'intestazione fuori.** Provata anche la versione compatta
  — una card sola per tutto l'elenco e i giorni come fasce dentro — ed è più densa e più
  brutta: i giorni smettono di leggersi come cose separate, che è tutto il motivo per cui
  l'elenco è raggruppato. Qui la densità non è l'obiettivo; l'obiettivo è trovare martedì.
- ⚠️ **Nella riga di un movimento l'aria non è il padding, è l'interlinea.** La scala dà
  body 15/22 e caption 13/18: due righe di testo sono 40 px per circa 28 px di lettere, e
  quei dodici il padding non li tocca — è il motivo per cui stringere il padding accorcia
  poco e imbruttisce molto. Quindi **le due righe qui vanno strette, 20 e 16**, il padding
  resta a dodici, e il badge scende a 36 px perché altrimenti diventa lui la cosa più alta
  della riga e il guadagno svanisce. È l'unico posto dell'app che si scosta dalla scala
  tipografica, ed è perché è l'unico dove due righe di testo sono un oggetto solo.
- Un movimento con data futura porta l'etichetta `futuro`: conta nel saldo, e quando il
  saldo non torna con la banca è la riga che lo spiega.
- ⚠️ **Un selettore a due vie non è una struttura.** Conti e Categorie ci sono passati per
  mezza giornata: su schermo stretto sembra ordinato, su desktop nasconde metà pagina e
  lascia una colonna vuota accanto all'altra metà. Se due cose meritano di stare separate
  meritano due sezioni; se non lo meritano, stanno una sotto l'altra. Il selettore serve a
  scegliere *una vista sugli stessi dati* — un periodo, un raggruppamento — non a nascondere
  contenuto diverso.
- ⚠️ **Righe per gli elenchi che si scorrono, card per le poche cose che si leggono.**
  Prima qui c'era scritto "righe per i soldi": sbagliato, e scoperto provandolo. Un elenco
  di movimenti si scorre cercandone uno, quindi gli importi vanno in colonna, sempre nella
  stessa posizione. Un conto invece non si scorre: sono sei, e ognuno è un nome e un numero
  che devono essere leggibili. Su 390px, nome + tipo + saldo + tre comandi sulla stessa riga
  non lasciano spazio a niente. **Conti e categorie sono card in griglia** (2 colonne da
  `sm`, 3 da `lg`), **i movimenti sono righe**.
- Nella card di un conto il **saldo ha la taglia `title`**: è quello per cui la card esiste.
  **Rosso se negativo**, perché un conto in rosso va notato senza dover leggere il segno.
- La riga di un trasferimento non somiglia né a un'entrata né a un'uscita: titolo
  "Conto → Conto", sottotitolo "Trasferimento", ciano, senza segno.

## Componenti

Forms: `Button` (primary/secondary/ghost/danger; primary una sola per schermata),
`IconButton`, `Field` (per importi: `type="text"` + `inputMode="decimal"`, mai
`type="number"`; stringa vuota = errore), `Chip`.
Display: `Card`, `Amount`, `TransactionRow`, `EmptyState`.
Navigation: `TabBar`. Feedback: `BusyOverlay`, `OfflineBanner`.

Riferimenti: token CSS in `tokens/`, specimen in `guidelines/`, implementazioni React in
`components/`, app dimostrativa in `ui_kits/wallet-app/`.
