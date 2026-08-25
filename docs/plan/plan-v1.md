# Piano — Wallet V1

> Prima stesura — 25 agosto 2026.
> Scritto **prima** di qualsiasi riga di codice: qui non c'è niente di già fatto, e le
> milestone sono tutte da fare. Quando l'implementazione comincerà, gli scostamenti si
> registrano qui man mano, come nel progetto da cui questo documento eredita la forma.

## Context

Oggi la tua finanza personale non sta da nessuna parte. Lo stipendio arriva su un conto, tu
lo smisti su altri conti, e le spese escono un po' da uno e un po' dall'altro. Sapere quanto
hai speso in un mese, o quanto hai in tutto, richiede di aprire tre home banking e fare i
conti a mente.

L'app deve diventare il **punto d'ingresso**: un posto dove i movimenti si registrano in
pochi secondi e dove, a fine mese, si vede senza fatica dove sono finiti i soldi e come si
muove il patrimonio.

La V1 si ferma alla **liquidità**: conti, movimenti, trasferimenti, categorie, grafici. Gli
investimenti — crypto, ETF, BTP, immobili — sono **V2**, e questo documento dice fin d'ora
come ci arriveranno, perché il modello della V1 deve poterli accogliere senza essere
riscritto.

Il repository contiene [`CLAUDE.md`](../../CLAUDE.md), [`README.md`](../../README.md) e
questo piano. Il design system non è ancora stato prodotto.

Questo documento descrive **le intenzioni**; `CLAUDE.md` descrive **le regole**. Quando il
codice comincerà a esistere e i due divergeranno, ha ragione `CLAUDE.md`, e lo scostamento
si registra qui.

## Decisioni prese

| Questione | Decisione |
|---|---|
| Nome del prodotto | **Wallet** |
| Piattaforma | Web app responsive, mobile-first, hosting gratuito, installabile come PWA |
| Utenti | **Uno solo** oggi. `household_id` su ogni tabella fin dal primo giorno, per non dover migrare il giorno in cui diventa condivisa |
| Inserimento movimenti | **Solo a mano** in V1. Import CSV e ricorrenti → V1.5 |
| Valuta | **Solo euro.** Importi interi in centesimi ovunque, euro solo a schermo: l'utente non incontra mai un centesimo |
| Conti | Tutti immediati: corrente, deposito, contante, prepagata. Nessun addebito differito |
| Saldi | **Derivati dai movimenti**, mai una colonna. Più il gesto di riconciliazione |
| Categorie | **Libere, un solo livello**, due elenchi separati: uscite ed entrate |
| Budget | Nessun tetto per categoria. Un solo **obiettivo di risparmio mensile** |
| Periodo | Mese solare di default, intervallo libero nei grafici |
| Grafici | **Recharts**, ridisegnata sui token del design system |
| Accesso | Magic link via email, sessione ~30 giorni |
| Interfaccia | Da produrre con Claude Design, versionata in `docs/design/` |
| Investimenti | V2 del prodotto, modello abbozzato in fondo a questo documento |

## Stack

**Frontend** — React + TypeScript + Vite + **Tailwind CSS 4**. Mobile-first. Niente Next.js:
il backend è Python, quindi il rendering server-side non serve e aggiungerebbe solo un
runtime in più.

**Backend** — Python + FastAPI. Pydantic per la validazione I/O, SQLAlchemy 2.0 + Alembic per
ORM e migrazioni.

**Database** — Postgres su Neon (free tier). NoSQL valutato e scartato: i dati sono
fortemente relazionali (conto → movimenti → categoria) e le due operazioni centrali — il
saldo di un conto e il totale per categoria in un periodo — sono una `SUM` con un `WHERE` e
una con un `GROUP BY`. Neon rispetto a Supabase: il free tier va in sospensione dopo pochi
minuti di inattività ma si risveglia da solo, mentre Supabase mette il progetto *in pausa*
dopo una settimana e va riattivato a mano dalla dashboard.

**Hosting** — tutto su Vercel piano Hobby (gratuito): frontend statico + backend FastAPI come
Serverless Function Python. **Piano B** se il runtime Python di Vercel dà problemi: backend su
Render free tier (funziona, ma dorme dopo 15 minuti e il primo accesso costa ~50 secondi).

**Email magic link** — API transazionale di Brevo, free tier da 300 email al giorno, nessun
dominio da verificare.

⚠️ Il vincolo "hosting totalmente gratuito" è quello che può far saltare l'architettura,
quindi **M0 esiste apposta per verificarlo prima** di scrivere logica di dominio.

⚠️ **Nessun collegamento automatico alla banca.** L'open banking (PSD2) passa da aggregatori
a pagamento — Tink, Nordigen/GoCardless, Salt Edge — e anche i piani "gratuiti" sono a
chiamate limitate e richiedono registrazione come soggetto autorizzato. È fuori dal vincolo
di costo e fuori dalla portata di un progetto personale. Da qui discende tutto il resto del
piano: **i dati li inserisci tu**, e quindi l'attrito di inserimento è il problema numero uno
del prodotto.

### Nota sulla sicurezza della sessione lunga

Trenta giorni sono comodi e vanno motivati con onestà, perché **qui i dati finanziari ci
sono**: questo database contiene dove tieni i soldi, quanti sono e cosa compri.

Il rischio accettato è "qualcuno con il telefono sbloccato apre l'app". Le mitigazioni non
sono facoltative: cookie `httpOnly` + `Secure` + `SameSite`, link di accesso **monouso e
valido 15 minuti** (quello vive in una casella email ed è l'anello debole vero), `/verify` in
POST così gli scanner antivirus dei provider non bruciano il token, token salvati solo come
SHA-256, refresh scorrevole della sessione, "esci da tutti i dispositivi" a due tocchi dal
profilo, e nessun importo o indirizzo nei log.

Se un giorno non dovesse bastare, la mossa non è accorciare la sessione — sarebbe fastidio
quotidiano in cambio di poco — ma un blocco locale con PIN o biometria all'apertura. Non è in
V1.

## Interfaccia — ⏳ da produrre

Il design system **non esiste ancora**. Verrà prodotto a parte con Claude Design e consegnato
in [`docs/design/DESIGN.md`](../design/DESIGN.md); da lì si ricava un set di token in
`frontend/src/styles/tokens.css` (blocco `@theme` di Tailwind 4), definiti una volta sola così
che i componenti non contengano valori arbitrari.

Fino ad allora **non si sceglie una palette e non si scrivono componenti "provvisori"**: è
esattamente il codice che poi resta. Quello che il design troverà già deciso:

- Le schermate: **Riepilogo, Movimenti, Conti, Analisi**, più profilo e impostazioni.
  Le categorie si gestiscono dalle impostazioni: le tocchi due volte l'anno, non meritano
  una scheda.
- ⚠️ **L'inserimento di un movimento è l'elemento più importante dello schermo.** Deve essere
  raggiungibile da ogni sezione, con un posto fisso, e costare tre tocchi: importo,
  categoria, salva. Tutto ciò che ne allunga la strada — un campo obbligatorio in più, una
  conferma, una schermata intermedia — va contestato in fase di design, non dopo.
- Su mobile il profilo è una quinta scheda; su desktop sta in fondo alla sidebar.
- Testi in italiano, sentence case, seconda persona informale, niente emoji.
- Numeri: `1.234,56 €`. Virgola decimale, punto per le migliaia, simbolo dopo con lo spazio.

Due schermate meritano attenzione particolare in fase di design, perché sono quelle che le
app di questo tipo sbagliano:

1. **L'elenco dei movimenti.** Deve reggere migliaia di righe, filtri combinati (periodo,
   conto, categoria, testo) e la lettura veloce: importo a destra, allineato, sempre nella
   stessa posizione. Un elenco di soldi si legge in colonna, non a paragrafi.
2. **La riga di un trasferimento.** Non è né un'entrata né un'uscita e non deve somigliare a
   nessuna delle due: se si legge come una spesa, tutto il senso del modello si perde
   nell'unico posto in cui l'utente guarda.

## Modello dati

### Gli importi

**Interi in centesimi, dal database allo stato del frontend.** `amount_cents`,
`BigInteger`. Niente virgola mobile in nessun punto del tragitto: `0.1 + 0.2` fa
`0.30000000000000004`, e su un anno di movimenti diventa un saldo che non torna con la banca
per due centesimi.

Un intero attraversa JSON senza perdere niente e resta esatto anche in JavaScript, dove i
numeri sono float64 ma rappresentano esattamente gli interi fino a 2^53 — novantamila
miliardi di euro, in centesimi. Da cui le due conseguenze che contano:

- **Il frontend può sommare, e lo fa.** Totale di una selezione, peso percentuale di una
  fetta, differenza fra due periodi: sono somme di dati che ha già in mano, e chiedere al
  server un numero che sa già calcolare sarebbe un giro inutile. ⚠️ Quello che il frontend
  **non** fa è decidere *cosa* sommare: la regola "un trasferimento non è una spesa" resta
  del dominio e arriva già applicata. La riga da non passare è la classificazione, non
  l'aritmetica.
- **La divisione per 100 avviene solo nel formattatore.** Appena dividi hai un float e hai
  buttato via il motivo per cui usavi gli interi. Si somma, si confronta e si ordina in
  centesimi; `formatMoney(cents)` è l'ultimo passo prima dello schermo.

⚠️ **L'utente non incontra mai un centesimo.** È una rappresentazione interna: si scrive
`12,50` e si legge `12,50 €`, in ogni campo, etichetta, errore ed esportazione. Le due
conversioni stanno in `domain/money.py` e `frontend/src/lib/money.ts`, e da nessun'altra
parte.

⚠️ **La conversione da testo a centesimi non è `parseFloat(x) * 100`.** `19.99 * 100` in
virgola mobile fa `1998.9999999999998`: troncato diventa `19,98`, cioè un centesimo perso su
buona parte degli importi. Si lavora sulle cifre — parte intera e decimale separate,
decimali riempiti o troncati a due, poi concatenate — senza passare da un numero con la
virgola. È il bug classico di questo modello e ha un test suo.

**Un effetto collaterale utile**: un intero si comporta identico su Postgres e su SQLite,
quindi la suite di test non può passare mentendo su una precisione che in produzione non
c'è. Con un tipo decimale sarebbe stato un rischio reale — SQLite non ne ha uno nativo e
SQLAlchemy ripiega sui float.

⚠️ Quando un importo si spezza in parti — le percentuali di una torta, una media — **il resto
va sull'ultima parte**: arrotondando ogni pezzo per conto suo la somma delle fette non fa più
il totale, e in un grafico si vede.

### Il punto centrale: tre tipi di movimento, una tabella sola

Un movimento è una riga. Il campo `kind` dice che cosa è, e da lì discende quali altri campi
hanno senso:

```
transaction
  kind          expense | income | transfer
  date          la data, non un istante
  amount_cents  intero positivo, sempre
  account_id    il conto toccato (per un transfer: quello da cui escono)
  counter_account_id   solo transfer: il conto in cui entrano
  category_id   solo expense e income; mai su un transfer
  description   facoltativa
  is_adjustment true solo per le rettifiche da riconciliazione
```

Due `CHECK` sul database tengono in piedi il modello, e non sono decorativi:

- `kind = 'transfer'` ⟺ `counter_account_id IS NOT NULL` **e** `category_id IS NULL`
- `counter_account_id <> account_id`

#### Esempio — il giro di un mese

Stipendio sul conto corrente, smistamento sul deposito, due spese e un prelievo:

| kind | data | importo | conto | contro-conto | categoria |
|---|---|---|---|---|---|
| `income` | 27/02 | 1.800,00 | Corrente | — | Stipendio |
| `transfer` | 27/02 | 500,00 | Corrente | Deposito | — |
| `transfer` | 28/02 | 100,00 | Corrente | Contante | — |
| `expense` | 02/03 | 62,40 | Corrente | — | Spesa |
| `expense` | 03/03 | 15,00 | Contante | — | Bar |

Cosa dicono i numeri di marzo, se il periodo è marzo: **uscite 77,40**, entrate 0,
risparmio −77,40. I due trasferimenti di febbraio non compaiono da nessuna parte se non nei
saldi dei conti, che è esattamente il punto.

⚠️ **Un trasferimento è una riga sola, non due.** La partita doppia è la scelta da manuale, e
qui è quella sbagliata: raddoppierebbe le righe di ogni elenco e obbligherebbe ogni schermata
e ogni statistica a filtrarne metà. Basta dimenticarsene una volta perché quei 500 € diventino
un'entrata, e da lì in poi ogni numero della dashboard è gonfio. Con una riga e due colonne,
**"un trasferimento non è una spesa" smette di essere una regola e diventa una proprietà della
tabella**.

Il prezzo di questa scelta è che il saldo di un conto si legge da due colonne invece che da
una — `Σ(dove account_id = X)` con segno e `Σ(dove counter_account_id = X)` in positivo — ed è
un prezzo che si paga una volta sola, dentro `domain/balances.py`.

### I saldi

⚠️ **Il saldo non è una colonna.** È sempre `opening_balance_cents + Σ movimenti`, calcolato.
Una colonna da aggiornare a ogni scrittura sarebbe un secondo numero che può contraddire il
primo, e in un'app di soldi due numeri discordi sono peggio di un numero solo lento.

```
saldo(conto) = opening_balance_cents
             − Σ amount_cents   dove kind = expense    e account_id = conto
             + Σ amount_cents   dove kind = income     e account_id = conto
             − Σ amount_cents   dove kind = transfer   e account_id = conto
             + Σ amount_cents   dove kind = transfer   e counter_account_id = conto
```

**Il patrimonio** è la somma dei saldi dei conti con `include_in_net_worth`. Quel flag esiste
perché non tutto ciò che vuoi tracciare è tuo: un conto cointestato, dei soldi di qualcun
altro. Toglie il conto dal totale del patrimonio e **non** lo toglie dalle statistiche di
spesa.

**Il patrimonio nel tempo** è lo stesso calcolo con un `date <= fine_mese`, ripetuto per ogni
mese. Su cinque anni sono sessanta somme sullo stesso insieme di movimenti: si fa in un
passaggio solo, accumulando mese per mese, non con sessanta query.

### La riconciliazione

⚠️ **"Il saldo vero oggi è X" genera un movimento, non una scrittura sul saldo.** L'app
calcola la differenza e registra una riga `is_adjustment` — `expense` se eri in meno, `income`
se eri in più — con `category_id` nullo.

Questa riga **muove il saldo e il patrimonio, e non muove le statistiche di spesa**. Non è
consumo: è la misura di quanto ti eri dimenticato di registrare. Metterla nella torta delle
categorie inventerebbe una spesa che non sai attribuire, e una torta falsa è peggio di una
torta con un buco dichiarato.

### Schema

```
household            lo spazio; una riga sola oggi
                     + monthly_savings_target_cents
app_user             email, household_id, display_name, preferences (JSON)
login_token          hash del token magic link, expires_at (15 min), used_at
session              refresh scorrevole, revoked_at

account              household_id, name, kind, opening_balance_cents, opening_date,
                     include_in_net_worth, position, is_archived
category             household_id, name, kind (expense|income), color, icon,
                     position, is_archived
transaction          household_id, date, kind, amount_cents, account_id,
                     counter_account_id, category_id, description, is_adjustment,
                     created_by_user_id, created_at, updated_at
```

Indici che non sono opzionali:

- `transaction (household_id, date DESC, id DESC)` — è l'ordine dell'elenco ed è la chiave
  della paginazione keyset.
- `transaction (household_id, account_id)` e `(household_id, counter_account_id)` — i saldi.
- `category (household_id, kind, lower(name))` **unico** — il nome è unico per segno, senza
  distinzione di maiuscole. Senza questo indice ti ritrovi "Bar" e "bar" e due fette nella
  stessa torta.

**Cosa non c'è, di proposito:**

- Nessuna tabella `budget`: c'è solo l'obiettivo di risparmio, che è un campo su `household`.
  Un valore solo, senza storia — se un giorno servirà, diventa una tabella con `valid_from`,
  e i mesi passati smetteranno di cambiare giudizio ogni volta che alzi l'asticella.
- Nessun `tag` sui movimenti. Le categorie bastano, e i tag sono la funzione che si usa per
  due settimane.
- Nessuna tabella per gli allegati/scontrini: richiederebbe uno storage di file, cioè un
  servizio in più e un costo.
- Nessun `recurring_transaction`: è V1.5, e va progettato quando ci sono dati veri da cui
  riconoscere i ricorrenti.

## Struttura del repository

```
backend/
  app/
    main.py             app FastAPI
    config.py           settings da variabili d'ambiente
    db.py               engine + sessione
    models/             SQLAlchemy
    schemas/            Pydantic, I/O delle API
    api/                router: auth, accounts, categories, transactions, stats
    domain/             ← logica di business pura, zero import di FastAPI o DB
      money.py            centesimi, parsing, arrotondamento, formattazione
      period.py           confini di periodo, mesi, etichette
      balances.py         saldi dei conti e patrimonio
      stats.py            aggregazioni: per categoria, per mese, confronti
      vocabulary.py       i tre enum chiusi
  migrations/           Alembic
  scripts/              manutenzione, da lanciare a mano
  tests/
frontend/
  src/
    api/                client tipizzato + cache delle letture
    features/dashboard/
    features/transactions/
    features/accounts/
    features/categories/
    features/settings/
    components/
    lib/                money.ts, period.ts, validation.ts, online.ts, pwa.ts
    styles/tokens.css   token derivati da docs/design/
api/index.py            entrypoint Vercel → monta l'app FastAPI
docs/
  plan/                 questo documento
  design/               specifiche di interfaccia — da produrre
```

La regola che tiene: **`domain/` non importa nulla di FastAPI né di SQLAlchemy.** Riceve liste
di oggetti semplici e restituisce oggetti semplici. È ciò che rende testabili senza database le
uniche cose che possono davvero sbagliare: somme, saldi e confini di periodo.

## Calcoli e algoritmi

Qui non c'è nessun algoritmo interessante, ed è una buona notizia: sono somme. Quello che
conta è **dove** si fanno e **cosa** includono.

### Dove si aggrega

⚠️ **In Python, non in SQL**, e la scelta è dichiarata insieme al suo limite. Il router carica
i movimenti del periodo, `domain/stats.py` li somma. Un anno di uso reale sono ~1.500
movimenti, cinque anni ~7.500: sommarli in memoria costa millisecondi, e in cambio ogni regola
di cosa-conta-e-cosa-no resta una funzione pura, testabile senza database.

**Oltre le decine di migliaia di righe** questo smette di valere e l'aggregazione va spostata
in SQL. Quando succederà, la tabella "cosa entra in cosa" di `CLAUDE.md` deve restare in un
posto solo: il momento in cui "spesa del mese" comincia a significare due cose leggermente
diverse a seconda di chi la chiede è il momento in cui l'app smette di essere affidabile.

### Cosa entra in cosa

| Numero | Include | Esclude |
|---|---|---|
| Uscite del periodo | `expense` | trasferimenti, rettifiche |
| Entrate del periodo | `income` | trasferimenti, rettifiche |
| Risparmio del periodo | entrate − uscite | trasferimenti, rettifiche |
| Saldo di un conto | tutto ciò che tocca quel conto, rettifiche comprese | niente |
| Patrimonio | saldi dei conti con `include_in_net_worth` | niente |

### La paginazione

⚠️ **Keyset su `(date DESC, id DESC)`, non `OFFSET`.** L'elenco dei movimenti cresce per
sempre e riceve inserimenti nel mezzo: con `OFFSET`, registrare una spesa retrodatata mentre
qualcuno sta scorrendo fa scivolare tutte le pagine successive, con righe che si ripetono e
righe che spariscono. Il cursore è l'ultima coppia `(date, id)` vista.

⚠️ **La paginazione non passa dalla cache delle letture.** `api/cache.ts` è una
stale-while-revalidate pensata per risposte intere che si sostituiscono; una lista che si
accumula per pagine non è quella cosa e si tiene per conto suo.

## Milestone

**M0 — Walking skeleton deployato.** Frontend minimo, `GET /api/health` che legge da Neon,
pagina `/_stato`, tutto online su Vercel. Serve a dimostrare che lo stack sta davvero nel piano
gratuito. Se qui emergono limiti, si cambia adesso e non a lavoro fatto.

**M1 — Accesso.** Magic link, sessione 30 giorni, invio via Brevo, schermata di profilo, "esci
da tutti i dispositivi". In parallelo, quando arriverà il design: token e componenti di base
(Button, IconButton, Card, Chip, Field).

**M2 — Conti e categorie.** CRUD di entrambi, saldo derivato, riconciliazione, archiviazione,
riordino. Qui dentro anche **`backup` e `restore`**: da questo momento in poi nel database c'è
roba inserita a mano, e da M3 ci sarà roba **irrecuperabile**. Il paracadute si mette prima di
saltare.

**M3 — Movimenti.** L'inserimento rapido (importo, categoria, salva), i trasferimenti, la
modifica e la cancellazione, l'elenco con filtri (periodo, conto, categoria, testo), ricerca e
paginazione keyset. È il cuore dell'app: se questa milestone è faticosa da usare, il resto non
serve a niente.

**M4 — Riepilogo e analisi. ← fine V1.** I grafici (elenco sotto), l'obiettivo di risparmio del
mese, il passaggio da un grafico ai movimenti che lo compongono.

**M5 — PWA e manutenzione.** Installabile e a schermo pieno, service worker per la sola shell,
fascia "sei senza rete". Più `doctor`, `prune`, `reset`, `users`, `merge_categories`,
`seed_demo`.

**V1.5 — Import e ricorrenti.** Import CSV dell'estratto conto con mappatura delle colonne,
riconoscimento dei duplicati e stato "da confermare"; movimenti ricorrenti (stipendio, affitto,
abbonamenti) **proposti e non inseriti d'ufficio** — un movimento che compare da solo e che non
è successo è peggio di un movimento mancante.

**V2 — Investimenti e patrimonio completo.** Sezione dedicata in fondo.

### I grafici della V1

Quattro sono richiesti, tre sono aggiunte che costano poco perché escono dalle stesse somme:

1. **Saldi per conto, totale e ultimi movimenti** — è la schermata di apertura, e risponde
   all'unica domanda che ti fai ogni giorno: quanto ho e cosa ho speso ieri.
2. **Uscite per categoria nel periodo** — barre orizzontali ordinate, con il peso percentuale.
   ⚠️ **Ogni fetta si apre** sui movimenti che la compongono: un numero che non si può aprire
   è un numero di cui non ti fidi.
3. **Andamento entrate / uscite / differenza, mese per mese** — la domanda "sto migliorando?".
4. **Patrimonio a fine mese** — la curva lunga, ed è il grafico che in V2 accoglierà anche gli
   investimenti senza cambiare forma.
5. **Confronto col periodo precedente, per categoria** — non "hai speso 340 in trasporti" ma
   "+120 rispetto al mese scorso". È il numero che dice qualcosa di azionabile.
6. **Le cinque uscite più grandi del periodo** — quasi sempre lì c'è la spiegazione di un mese
   storto, e trovarla scorrendo l'elenco costa fatica.
7. **Spesa media giornaliera e proiezione a fine mese** — l'unico numero che a metà mese ti
   dice qualcosa che puoi ancora cambiare. ⚠️ Va mostrato come proiezione lineare e nient'altro:
   non è una previsione, ed è onesto dirlo nell'etichetta.

⚠️ **Un periodo senza dati si dice a parole, non si disegna.** Un grafico vuoto con gli assi a
zero si legge come "hai speso zero", che è tutta un'altra affermazione.

## V2 del prodotto — Investimenti e patrimonio completo

Oggi il patrimonio che l'app conosce è solo la liquidità sui conti. La V2 aggiunge il resto:
crypto, ETF, obbligazioni e BTP, immobili, e qualunque altra cosa abbia un valore che cambia.

Non è in V1 per una ragione precisa: **la liquidità si registra, gli investimenti si
valutano**, e sono due meccaniche diverse. Un conto ha movimenti e un saldo derivato; un
immobile ha una stima che cambia quando decidi tu, un bitcoin ha un prezzo che cambia ogni
minuto. Mescolarle nella stessa tabella significherebbe piegare il modello dei movimenti a
qualcosa che non è.

### Modello dati aggiuntivo

```
asset             household_id, name, kind (crypto|etf|obbligazione|immobile|altro),
                  quantity, unit_or_ticker, is_liquid, currency,
                  opened_at, closed_at, notes
asset_valuation   asset_id, date, value_cents, source (manual|api), source_ref,
                  imported_at
```

⚠️ **`quantity` non è un importo, ed è l'unico campo decimale del progetto.** Un bitcoin si
conta a otto decimali (`NUMERIC(28, 8)`), un ETF a frazioni di quota: gli interi non bastano
e la scala non è quella dei soldi. `value_cents` invece è un controvalore in euro e segue la
regola di tutti gli altri importi. Sono due tipi diversi perché sono due cose diverse, e
confonderli tronca la quantità di crypto al centesimo di unità.

⚠️ **Le valutazioni sono istantanee datate, mai un campo sovrascritto.** Un solo "valore
attuale" aggiornato in place renderebbe il grafico del patrimonio nel tempo una bugia
retroattiva: il patrimonio di marzo verrebbe ricalcolato col prezzo di agosto, e la curva che
guardi non sarebbe mai stata vera. La storia si accumula, come i movimenti.

Il patrimonio totale diventa: **saldi dei conti** (già calcolati) **+ ultima valutazione nota
di ogni asset aperto**. La forma del grafico non cambia, cambia cosa ci si somma dentro.

### Da dove arrivano i prezzi

- **Crypto — CoinGecko free.** Nessuna chiave API, endpoint pubblico, rate limit basso ma
  ampiamente sufficiente: **una chiamata al giorno basta e avanza**. Tu dici quanti bitcoin
  hai, l'app scrive una `asset_valuation` al giorno. È l'unico pezzo davvero automatizzabile a
  costo zero, ed è anche quello che cambia di più: la combinazione giusta.
- **ETF e titoli — a mano, per ora.** Non esiste una fonte gratuita e affidabile *a lungo
  termine*: le API di quotazioni serie sono a pagamento, e gli endpoint non ufficiali (Yahoo e
  simili) si rompono senza preavviso e senza licenza d'uso. Meglio un valore inserito a mano
  una volta al mese, che è la frequenza con cui un ETF va guardato, che una pipeline che
  smette di funzionare a gennaio e te ne accorgi a giugno.
- **BTP e obbligazioni — a mano**, con la stessa logica. Un BTP tenuto a scadenza ha un valore
  nominale noto: la stima è più stabile di quanto sembri.
- **Immobili — sempre e solo a mano.** Non esiste un prezzo, esiste una tua stima. Va trattata
  come tale.

⚠️ **Una chiamata a un servizio esterno che fallisce non deve rompere la schermata.** Se
CoinGecko non risponde, si mostra l'ultima valutazione nota con la sua data. Vale la regola
generale del progetto: prevedere sempre un fallback.

### Le due regole di onestà

⚠️ **Ogni numero porta con sé la sua data.** Se l'ultima valutazione di un asset è di tre
settimane fa, il patrimonio si mostra *con* quella data, non come se fosse di adesso. Un
totale che sembra attuale e non lo è è peggio di nessun totale: sul secondo controlli, del
primo ti fidi.

⚠️ **Liquido e vincolato si separano.** Un immobile e un BTP a scadenza non sono soldi
disponibili. `is_liquid` esiste perché il patrimonio si legga su due righe — quanto ho, e
quanto potrei usare domani — che sono due domande diverse e vengono confuse di continuo.

### Cosa mostra, e cosa non deve fare

`CLAUDE.md` è netto: l'app non è uno strumento di consulenza finanziaria. La V2 **descrive,
non prescrive**.

Mostra: composizione del patrimonio per tipo di asset, andamento nel tempo, quanto pesa
ciascuna posizione, liquido contro vincolato.

Non fa: proiezioni di rendimento, confronti con benchmark presentati come voto, suggerimenti
di allocazione o ribilanciamento, avvisi del tipo "sei troppo esposto su crypto". **Disclaimer
visibile** nella schermata del patrimonio, non nascosto in un footer.

## Test

Poco ma mirato, concentrato su `domain/` che è puro e quindi banale da testare (pytest):

- ⚠️ **Un trasferimento non compare mai fra entrate o uscite.** In nessun periodo, con nessun
  raggruppamento, in nessuna delle due direzioni. **È il test intoccabile di questo progetto**,
  l'equivalente del vincolo alimentare rigido nel progetto sorgente: se cade questo, ogni
  numero mostrato dall'app è sbagliato.
- Il saldo di un conto è esattamente `opening_balance_cents + Σ movimenti`, e un trasferimento lo
  muove nella direzione giusta **da entrambi i lati**.
- Il patrimonio ignora i conti con `include_in_net_worth = false`, e le loro spese invece
  contano nelle statistiche.
- Una rettifica muove saldo e patrimonio e **non** muove uscite, entrate né risparmio.
- Aritmetica in centesimi: sommare mille importi da `0,01 €` fa esattamente `10,00 €`; le
  percentuali di una torta sommano a 100 anche quando i pezzi non sono divisibili (l'ultima
  fetta assorbe il resto, non si arrotondano tutte per conto loro).
- Confini di periodo: un movimento del primo e uno dell'ultimo giorno del mese cadono nel mese
  giusto; un intervallo libero include entrambi gli estremi; il "periodo precedente" di un
  mese è il mese prima, non 30 giorni prima.
- Il patrimonio a fine di un mese senza movimenti è uguale a quello del mese precedente.
- Paginazione keyset: inserire un movimento retrodatato fra due pagine non duplica né salta
  righe già viste.
- Conversione fra testo ed euro: `12,50`, `12.50`, `1.234,56` e ` 12,5 ` danno rispettivamente
  `1250`, `1250`, `123456` e `1250` centesimi; **la stringa vuota è un errore, non zero**; un
  importo negativo, a zero o con tre decimali viene rifiutato dallo schema.
- ⚠️ **`19,99` fa `1999`, non `1998`.** È il caso che casca se qualcuno scrive la conversione
  come `parseFloat(x) * 100`, e va provato su tutta la fascia dei valori con `,99`.
- Formattazione: `1250` esce come `12,50 €` e `123456` come `1.234,56 €`; nessuna stringa
  mostrata all'utente contiene un valore in centesimi.
- Un movimento con categoria di segno sbagliato (una categoria `income` su una `expense`) viene
  rifiutato; un trasferimento con categoria viene rifiutato; un trasferimento sullo stesso
  conto viene rifiutato.

Niente test sui componenti React in V1: cambiano troppo in fretta per valere il costo.

## Verifica

1. `cd backend && uvicorn app.main:app --reload` + `npm run dev`
2. `pytest` — la suite di dominio passa, incluso il test sui trasferimenti
3. `alembic upgrade head` su un database pulito
4. A mano, dal telefono, il giro reale di un mese: accesso via magic link → crea tre conti con
   i loro saldi iniziali → crea le categorie che usi davvero → registra lo stipendio → smista
   con due trasferimenti e **verifica che entrate e uscite del mese non si siano mosse** →
   registra una decina di spese su conti diversi → controlla che i saldi tornino con l'home
   banking → riconcilia un conto e verifica che la rettifica muova il saldo e non la torta →
   apri l'analisi, scendi da una fetta ai movimenti, cambia periodo → archivia una categoria e
   verifica che sparisca dalla scelta e resti nei grafici del passato
5. Deploy su Vercel e ripetere il punto 4 in produzione
6. `python -m scripts.backup` e riapertura del file: dentro devono esserci tutti i movimenti

## Dipendenze

Approvate:

**Backend** — `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `psycopg`, `pydantic-settings`,
`pytest`.
**Frontend** — `react`, `react-router`, `vite`, `typescript`, `tailwindcss`, **`recharts`**.

`recharts` è l'unica aggiunta rispetto allo stack sorgente ed è stata approvata
esplicitamente: i grafici sono metà del valore della V1 e disegnarli a mano in SVG sarebbe
stato un progetto dentro il progetto. Va però **ridisegnata sui token**, non usata con
l'aspetto di default.

Non approvate e non da introdurre senza chiedere: librerie di data fetching (TanStack Query),
librerie di form, librerie di date (`period.py`/`period.ts` bastano), librerie di componenti.

## Punti aperti da decidere durante l'esecuzione

1. **Raggruppamento dell'elenco movimenti**: per giorno con un'intestazione, o piatto? Dipende
   da quanti movimenti ci sono davvero in una giornata. Si decide a M3 guardando i dati veri.
2. **Colore e icona delle categorie**: quanto lasciare scegliere e quanto proporre. Una palette
   libera produce dieci categorie di dieci sfumature di blu; una chiusa non basta mai. Si
   decide col design.
3. **Taratura dell'obiettivo di risparmio**: il numero giusto si scopre dopo due o tre mesi di
   dati veri, non prima.
4. **Categorie iniziali**: proporne un elenco al primo accesso o partire dal foglio bianco? Il
   foglio bianco è più onesto ma l'elenco toglie attrito il primo giorno. Da valutare a M2.
5. **Movimenti futuri**: registrare una spesa con data futura si deve poter fare? Se sì, i
   saldi "di oggi" devono escluderla, e questo è un `WHERE date <= today` da mettere in un
   posto solo. Da decidere a M3.
