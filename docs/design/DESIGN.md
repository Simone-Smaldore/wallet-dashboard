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
#5C6F65`. I colori delle categorie escono da questa palette.

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

- Spaziatura: 4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48. Margine pagina 16, padding card
  16, gap fra card 12. Target tattile minimo 44px. Tab bar 64, FAB 56.
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
- Trasferimenti: `arrow-left-right`, icona in contenitore **quadrato** (raggio 12); le
  categorie in contenitore rotondo.
- Niente emoji, niente unicode come icone, niente SVG disegnati a mano.
- **Nessun logo**: wordmark tipografico "Wallet." in Space Grotesk 600, punto finale in
  `--accent`.

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
  titolo, sottotitolo `categoria · conto · data` (troncato con ellissi, mai a capo).
- ⚠️ **Un selettore a due vie non è una struttura.** Conti e Categorie ci sono passati per
  mezza giornata: su schermo stretto sembra ordinato, su desktop nasconde metà pagina e
  lascia una colonna vuota accanto all'altra metà. Se due cose meritano di stare separate
  meritano due sezioni; se non lo meritano, stanno una sotto l'altra. Il selettore serve a
  scegliere *una vista sugli stessi dati* — un periodo, un raggruppamento — non a nascondere
  contenuto diverso.
- **Righe per i soldi, tessere per le etichette.** Un saldo è un numero e va in colonna,
  sempre nella stessa posizione; una categoria è un'icona, un colore e una parola, e sta in
  una griglia che riempie la larghezza (2 colonne da `sm`, 3 da `lg`).
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
