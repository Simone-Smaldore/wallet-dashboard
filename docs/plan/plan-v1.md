# Piano — Wallet V1

> Prima stesura — 25 agosto 2026, scritta prima di qualsiasi riga di codice.
> Revisione dello stesso giorno: il design è arrivato e M0 è stata costruita, quindi le due
> sezioni corrispondenti non descrivono più intenzioni. Gli scostamenti si registrano qui
> man mano, come nel progetto da cui questo documento eredita la forma.

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
questo piano, più il design system in [`docs/design/`](../design/).

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

## Interfaccia — ✅ conclusa

Il design system è stato prodotto con **Claude Design** ed è in
[`docs/design/DESIGN.md`](../design/DESIGN.md), con l'immagine di riferimento in
[`docs/mockup/`](../mockup/). I token sono travasati in `frontend/src/styles/tokens.css`
(blocco `@theme` di Tailwind 4) da M0, definiti una volta sola così che i componenti non
contengano valori arbitrari.

In sintesi: **cruscotto notturno**, tema solo scuro, fondo `#060A08`, unico accento verde
`#3DF29B` col glow riservato all'azione primaria e al FAB, Space Grotesk per display e
**tutti i numeri** (tabulari) e Instrument Sans per il testo, forme arrotondate (card 16,
controlli 12, pillole 999), icone Lucide, nessun logo ma un wordmark tipografico. Testi in
italiano, sentence case, seconda persona informale.

⚠️ **I quattro colori del denaro sono semantica, non decorazione**: entrate verdi col `+`,
uscite rosse col `−`, **trasferimenti ciano e senza segno**, rettifiche ocra. È il design che
ratifica la regola di dominio.

Quello che il design ha confermato di quanto era già deciso:

- ⚠️ **L'inserimento di un movimento è l'elemento più importante dello schermo.** Deve
  costare tre tocchi: importo, categoria, salva. Tutto ciò che ne allunga la strada — un
  campo obbligatorio in più, una conferma, una schermata intermedia — va contestato subito.
- Numeri: `1.234,56 €`. Virgola decimale, punto per le migliaia, simbolo dopo con lo spazio.

⚠️ **La navigazione è cambiata due volte, e le due versioni sono registrate in DESIGN.md.**
Dove si è fermata: **cinque sezioni** — Riepilogo, Movimenti, Conti, **Categorie**, Analisi
— con il profilo fuori dalle schede (in alto a destra su telefono, in fondo alla sidebar su
desktop) e il **+ flottante** accanto alla tab bar invece che al suo centro. Le categorie
sono uscite dalle impostazioni: il piano diceva "le tocchi due volte l'anno", che è vero a
regime e falso proprio quando le configuri.

⚠️ Come nell'altro progetto, i riferimenti in fondo a DESIGN.md (`tokens/`, `guidelines/`,
`components/`, `ui_kits/wallet-app/`) **non sono nel repository**: è arrivato solo il
documento.

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

**M0 — Walking skeleton. ✅ fatto in locale, da deployare.** Frontend minimo,
`GET /api/health` che legge da Neon, pagina `/_stato`, i token del design system, Alembic
configurato a vuoto. Serve a dimostrare che lo stack sta davvero nel piano gratuito, e
finché non è online su Vercel quella dimostrazione non è completa.

Due cose scoperte strada facendo:

- ⚠️ **`"framework": null` in `vercel.json` è la riga che tiene in piedi l'architettura.**
  La documentazione Vercel marca ormai come legacy le funzioni in `/api` e, se rileva
  FastAPI in `requirements.txt`, attiva il preset Python che **ha la precedenza sui
  file-based functions**: il rewrite verso `/api/index` smetterebbe di significare
  qualcosa. Quella riga disattiva il rilevamento. Senza, l'alternativa sarebbe il preset
  più `app.frontend()`, che è la strada consigliata per i progetti nuovi ma che qui
  cambierebbe layout e documenti senza guadagno.
- **Lo scheletro è rispecchiato da food-plan-maker**, non riscritto: stessi pin di
  versione, stesso `api/index.py`, stesso `db.py`, stesso `migrations/env.py`. Le trappole
  già pagate là (host `-pooler`, `NullPool`, `postgresql+psycopg://`, `httpx2` per il
  TestClient) sono arrivate qui gratis.

Un'aggiunta rispetto al progetto sorgente: `/api/health` fa passare il `detail` da
`redact_dsn` prima di restituirlo. Quella pagina sta fuori dal login e il driver, quando
fallisce, cita la stringa di connessione con dentro la password.

**M1 — Accesso. ✅ fatto.** Magic link, sessione 30 giorni che scorre a ogni uso, invio via
Brevo, profilo, "esci da tutti i dispositivi". Più la prima migrazione (`household`,
`app_user`, `login_token`, `session`) e i componenti di base dai token: `Button`, `Field`,
`Card`, `EmptyState`, `BusyOverlay`.

Il flusso è ripreso quasi per intero dal progetto di riferimento, dove è in produzione da
mesi: `domain/auth.py` puro, `deps.py` con la sessione che scorre, il sender Brevo con lo
user-agent esplicito, `lib/pwa.ts` per il caso iOS. Non c'era ragione di riprogettarlo.

Tre scostamenti, tutti decisi in corsa:

- **La scocca è entrata a M1**, non a M2: quattro sezioni segnaposto più il profilo, così la
  navigazione esiste prima delle schermate invece di essere rifatta attorno a esse.
- ⚠️ **Cinque schede e il FAB flottante**, non quattro col FAB al centro come nel design. Il
  profilo su telefono non aveva una strada; gliela dà la quinta scheda, e il bottone **+**
  si stacca dalla barra restando in basso a destra. `DESIGN.md` è stato aggiornato: il
  principio "l'inserimento ha un posto fisso" regge, cambia dove quel posto sta.
- **`lucide-react` è entrata** come dipendenza, come prescrive DESIGN.md.

Una piccola aggiunta rispetto al sorgente: `logout` e `logout-all` azzerano il contesto
lato client **qualunque cosa risponda il server**. Se la chiamata fallisce, tenere l'utente
in memoria lascerebbe l'app che sembra dentro mentre ogni richiesta risponde 401.

**M2 — Conti e categorie. ✅ fatto.** CRUD di entrambi, saldo derivato, archiviazione,
riordino, e **`backup` e `restore`**: da questo momento in poi nel database c'è roba
inserita a mano, e da M3 ci sarà roba **irrecuperabile**. Il paracadute si mette prima di
saltare.

Tre scostamenti dal piano:

- ⚠️ **La tabella `transaction` è nata qui**, con i suoi CHECK, pur non essendo scritta da
  nessuna schermata. Le sue regole *sono* il modello — importo intero positivo, il segno nel
  `kind`, il trasferimento come riga sola — e `domain/balances.py` è potuto nascere testato
  mentre la superficie era ancora piccola. Il saldo mostrato è già
  `saldo_iniziale + Σ movimenti` su una somma vuota: la formula è vera, non un segnaposto.
- **La riconciliazione è slittata a M3.** Genera una rettifica, e a M2 non esisteva una
  schermata dove vederla comparire: un gesto che crea una riga invisibile è peggio del
  gesto che manca.
- ⚠️ **Le categorie stanno dentro Conti**, non nelle impostazioni come diceva `CLAUDE.md`.
  Sono le due anagrafiche dell'app e la loro casa è insieme.

Una scoperta durante l'implementazione: **il punto decimale è ambiguo e va deciso**.
`1.234` è milleduecentotrentaquattro euro, `12.50` è dodici e cinquanta, e si scrivono
entrambi. La regola in `domain/money.py` e nel suo specchio `lib/money.ts`: una stringa
fatta solo di gruppi di migliaia ben formati si legge come migliaia, in tutto il resto
l'ultimo punto è il separatore decimale. La virgola non è mai ambigua.

Le categorie iniziali (dieci di uscita, quattro di entrata) sono **seminate dalla
migrazione**: al primo accesso c'è da cosa partire invece di quattordici form fra te e la
prima spesa registrata. Sono una proposta, si archiviano.

**M3 — Movimenti. ✅ fatto.** L'inserimento in un foglio dal basso raggiungibile da ogni
sezione, l'elenco raggruppato per giorno con filtri, ricerca e paginazione keyset, modifica
e cancellazione, trasferimenti, e la riconciliazione slittata da M2.

I due punti che il piano lasciava aperti sono chiusi:

- **L'elenco è raggruppato per giorno**, con il totale speso in testa a ogni giornata. Si
  scorre cercando "martedì" invece di leggere venti date ripetute. ⚠️ Nel totale vanno
  **solo le uscite**: un trasferimento sposta senza spendere e una rettifica misura quello
  che avevi dimenticato, e sommarli farebbe sembrare peggiore una giornata proprio nel
  numero che si guarda di sfuggita.
- ⚠️ **I movimenti futuri si registrano e contano subito nel saldo.** Il numero risponde a
  "quanto mi resterà"; il prezzo è che finché non avvengono non coincide con la banca. Una
  sola eccezione, obbligatoria: **la riconciliazione si ferma a oggi**. Senza quel taglio
  la differenza includerebbe l'affitto della settimana prossima e la rettifica sarebbe un
  movimento inventato che resta in archivio.

Due decisioni prese in corsa:

- **La categoria che manca si crea dentro il foglio**, chiedendo solo il nome. Colore e
  icona li assegna il server. Mandare qualcuno in un'altra sezione a metà di un
  inserimento è il modo migliore per fargli scegliere "Altro" per sempre.
- **I movimenti si cancellano**, non si archiviano: un movimento sbagliato non è storia, è
  un errore di battitura.

**M4 — Riepilogo e analisi. ✅ fatto — il prodotto della V1 è chiuso.** Il riepilogo con
patrimonio, saldi, totali del mese e obiettivo di risparmio; l'analisi con uscite per
categoria, andamento mensile, patrimonio nel tempo, le uscite più grandi e il ritmo di
spesa; e il passaggio da ogni numero ai movimenti che lo compongono.

Il pezzo che conta è `backend/app/domain/stats.py`: la tabella "cosa entra in cosa" di
`CLAUDE.md` è diventata due funzioni, `is_spend` e `is_income`, e ogni numero dei due
cruscotti esce da lì. `api/stats.py` carica i movimenti una volta e non decide niente. Il
test intoccabile ha adesso la sua seconda metà — `balances` dimostra che un trasferimento
non può *muovere* un totale, `stats` che non può *comparire* in uno.

Sei scostamenti dal piano, tutti scoperti costruendo:

- ⚠️ **Le uscite per categoria non usano Recharts.** Ogni riga deve portare nome, importo,
  quota e variazione e restare leggibile a 390px: è un elenco con dentro una barra, non un
  grafico, e con la libreria la prima cosa a essere troncata sarebbero le etichette.
  Recharts resta per le due serie temporali, che è dove serve davvero.
- ⚠️ **La schermata Analisi si carica a parte.** Recharts pesa 120 kB gzippati, più di tutta
  l'app prima di lei, e serve a una rotta sola. Compilata dentro, quel peso sarebbe finito
  anche sulla schermata di inserimento — quella che si usa in piedi alla cassa, dove la
  priorità del prodotto è che registrare una spesa costi tre tocchi e nessuna attesa. I
  grafici si guardano una volta al mese, dal divano, e possono permettersi di scaricarsi.
- **Un endpoint per schermata, non uno per grafico.** Il Riepilogo si apre più volte al
  giorno contro una function che parte fredda, e i numeri di una schermata sono viste sugli
  stessi movimenti, che il server ha già in mano.
- ⚠️ **I filtri dei Movimenti sono passati nella query string.** È la condizione perché un
  grafico si possa aprire: da una fetta si arriva all'elenco con lo stesso periodo e la
  stessa categoria con cui il numero è stato calcolato, e la risposta a "e da dove esce?"
  diventa una pagina che si può ricaricare, condividere e da cui si torna indietro.
- **L'obiettivo di risparmio si modifica dal Riepilogo**, non dal profilo: si tara guardando
  i mesi che hai avuto davvero, quindi sta dove li guardi. `null` significa "non me lo sono
  dato" e non zero — un obiettivo a zero mostrerebbe una barra piena per il motivo
  sbagliato.
- **Le quote sono interi in millesimi**, come gli importi sono interi in centesimi, e il
  resto va sull'ultima fetta con qualcosa dentro: fette che sommano a 99,7 % accanto a un
  grafico si vedono a occhio.

Dopo i primi giorni d'uso reale, tre cose sono cambiate:

- ⚠️ **L'obiettivo di risparmio si giudica da uno stipendio al successivo**, non sul mese
  solare. I soldi arrivano il 27 e la domanda è se lo stipendio di novembre c'era ancora
  quando è arrivato quello di dicembre; il primo del mese taglia quella tratta a metà. Il
  verdetto sta sul ciclo chiuso — l'unico la cui spesa è finita — e il ciclo in corso
  mostra invece **quanto si può ancora spendere**, che è l'unico numero su cui si può
  ancora agire. Dettaglio delle regole in `CLAUDE.md`.
- ⚠️ **Anno e trimestre sono solari**, non finestre mobili di 12 o 3 mesi: una finestra
  mobile vuol dire una cosa diversa ogni volta che la apri, e "l'anno" detto a voce non ha
  mai significato "da agosto scorso". Di conseguenza anche `previous_period` confronta un
  qualsiasi periodo fatto di **mesi interi** con lo stesso numero di mesi prima.
- ⚠️ **Il selettore offre solo i periodi che hanno dati** (`/api/stats/calendar`), e le
  frecce si fermano ai bordi. Sette grafici vuoti che spiegano ognuno che non c'è niente
  fanno sembrare rotta la schermata; l'unica eccezione è l'intervallo libero, dove le due
  date le hai scritte tu. Accanto alle frecce c'è una combobox: tornare a febbraio 2020 non
  può costare settantadue clic.

Sistemata anche una divergenza lasciata da M3: `frontend/src/api/client.ts` conosceva sei
colori di categoria e il backend dieci, quindi il selettore ne offriva sei e il colore
assegnato dal server poteva essere uno che il form non sapeva mostrare come selezionato.

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

1. ~~**Raggruppamento dell'elenco movimenti**~~ → chiuso a M3: per giorno, con il totale
   delle sole uscite in testa.
2. **Colore e icona delle categorie**: quanto lasciare scegliere e quanto proporre. Una palette
   libera produce dieci categorie di dieci sfumature di blu; una chiusa non basta mai. Si
   decide col design.
3. **Taratura dell'obiettivo di risparmio**: il numero giusto si scopre dopo due o tre mesi di
   dati veri, non prima.
4. **Categorie iniziali**: proporne un elenco al primo accesso o partire dal foglio bianco? Il
   foglio bianco è più onesto ma l'elenco toglie attrito il primo giorno. Da valutare a M2.
5. ~~**Movimenti futuri**~~ → chiusi a M3: si registrano e **contano subito** nel saldo. Il
   `WHERE date <= today` esiste in un posto solo — il parametro `as_of` di
   `domain/balances.py` — e ha un chiamante soltanto: la riconciliazione.
