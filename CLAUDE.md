# CLAUDE.md

> Stato: **la V1 è finita, M0 → M5.** Si entra con un magic link, ci sono conti e
> categorie, si registrano movimenti (uscite, entrate e trasferimenti) con elenco filtrabile
> e riconciliazione dei saldi, ci sono il riepilogo, i grafici e l'obiettivo di risparmio
> giudicato da uno stipendio al successivo, l'app si installa sulla home, e ci sono tutti e
> otto gli script di manutenzione.
>
> Il prossimo passo è la **V1.5** (import CSV, movimenti ricorrenti), poi la **V2**
> (investimenti). Entrambe descritte nel piano.
>
> Questo file è la fonte di verità operativa: raccoglie le decisioni prese e, soprattutto,
> **i motivi per cui sono state prese così**. Ormai quasi tutto quello che c'è scritto
> descrive codice che esiste; dove una regola parla di un file che non c'è ancora sta
> dicendo *dove quella cosa dovrà stare*.
>
> Il piano in [`docs/plan/plan-v1.md`](docs/plan/plan-v1.md) descrive le intenzioni e le
> milestone; questo file descrive le regole. Quando il codice comincerà a esistere, questo
> file avrà ragione sul piano — perché il piano racconta cosa volevamo e questo cosa c'è.
> Se trovi una divergenza, segnalamela.
>
> `DEVELOPER.md`, la spiegazione dell'architettura per un essere umano che arriva nuovo sul
> codice, si scrive dopo M1: prima non avrebbe niente da raccontare.

## Cos'è questo progetto

**Wallet** — web app per il **controllo della finanza personale**. Registra i movimenti su
N conti, tiene i trasferimenti fra un conto e l'altro, li categorizza, e da lì ricava
saldi, patrimonio e grafici.

Il nome del prodotto è **Wallet**, e si scrive così ovunque: wordmark, `<title>`, titolo
dell'API. La cartella del repository si chiama `wallet-dashboard` per ragioni storiche; il
prodotto no.

Progetto personale, singolo sviluppatore, un solo utente. Priorità: farlo funzionare bene
per una persona prima di pensare a scalare.

**Uso reale: due momenti diversi, e l'app deve servirli entrambi.**

1. **Trenta secondi in piedi, appena pagato.** Registrare una spesa deve costare tre
   tocchi: importo, categoria, salva. Il conto è quasi sempre lo stesso, la data è quasi
   sempre oggi, e ogni campo che chiede attenzione qui è un campo per cui prima o poi
   smetterai di registrare le spese. **Un'app di finanza personale muore di attrito
   all'inserimento, non di mancanza di funzionalità.**
2. **Mezz'ora tranquilla a fine mese.** Guardare dove sono finiti i soldi, confrontare col
   mese prima, vedere il patrimonio salire o scendere. Qui servono i grafici, i filtri e
   la calma.

Tutto il prodotto ruota attorno a questi due momenti, e sono in tensione fra loro: il
primo vuole meno campi possibili, il secondo vuole dati completi. Dove sono in conflitto,
**vince il primo**: un dato mancante si corregge a fine mese, un dato mai registrato è
perso per sempre.

## Obiettivi e non-obiettivi

**Obiettivi (V1)**
- Registrare spese ed entrate su più conti, in pochi secondi
- Modellare i trasferimenti fra conti senza che vengano scambiati per spese
- Categorizzare i movimenti e correggerne la categoria dopo
- Sapere quanto c'è su ogni conto e quanto vale il totale, oggi e nel tempo
- Mostrare dove finiscono i soldi: per categoria, nel tempo, rispetto al mese scorso
- Un obiettivo di risparmio mensile, da confrontare col reale

**Non-obiettivi (per ora)**
- App mobile nativa
- Collegamento automatico alla banca (PSD2/open banking): sono servizi a pagamento, e il
  vincolo di questo progetto è che resti gratuito
- Import di estratti conto e movimenti ricorrenti → **V1.5**, non V1
- Investimenti, crypto, immobili → **V2**, ma il modello della V1 deve poterli accogliere
- Budget con tetti per categoria: c'è **solo** l'obiettivo di risparmio complessivo
- Multivaluta: **V1 è solo euro**, dichiarato e non aggirato
- Account separati, ruoli o permessi: oggi c'è **un utente solo**

## Stack

Identico a quello di un altro progetto personale già in produzione su Vercel, e questa non
è pigrizia: è uno stack di cui conosco già le trappole, e ogni pezzo qui sotto ha una
motivazione che vale anche per questo dominio.

| Livello | Scelta | Perché |
|---|---|---|
| Frontend | React + TypeScript + Vite + Tailwind CSS | Mobile-first: le spese si registrano dal telefono, i grafici si guardano dal PC. Niente Next.js, il backend è Python e il rendering server-side non servirebbe a nulla |
| Backend | Python + FastAPI, Pydantic | È il linguaggio che padroneggio meglio |
| ORM / migrazioni | SQLAlchemy 2.0 + Alembic | |
| Database | Postgres su Neon (free tier) | Dati fortemente relazionali e aritmetica esatta: gli importi sono interi in centesimi e i saldi sono somme, cioè esattamente quello che un relazionale fa senza sbagliare. Neon anziché Supabase perché il free tier di Supabase mette il progetto in pausa dopo una settimana e va riattivato a mano, Neon si risveglia da solo |
| Hosting | Vercel Hobby: statico + FastAPI come serverless function | **Vincolo assoluto: deve restare gratuito.** Piano B: backend su Render free tier |
| Autenticazione | Magic link via email, sessione ~30 giorni | Nessuna password da ricordare da telefono |
| Email | API transazionale di Brevo (300/giorno gratis) | Zero costi e **nessun dominio da verificare**: basta un singolo mittente confermato |
| Grafici | Recharts | Approvata esplicitamente, ed è l'**unica** dipendenza nuova rispetto allo stack sorgente. Vedi la sezione "I grafici" per i vincoli d'uso |

**Nessun LLM in V1** — vedi la sezione dedicata più sotto.

## Comandi

Verificati a valle di M0. Il frontend è un **npm workspace**: `npm` si lancia dalla radice,
non da `frontend/`.

```bash
# installazione (una tantum)
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements-dev.txt
npm install

# dev server backend — http://127.0.0.1:8000, docs su /api/docs
cd backend && uvicorn app.main:app --reload

# dev server frontend — http://localhost:5173, proxy /api verso uvicorn
npm run dev

# build frontend (produce frontend/dist)
npm run build

# test
cd backend && pytest

# typecheck frontend
npm run typecheck

# migrazioni DB — si lanciano a mano dalla tua macchina contro Neon,
# mai in fase di deploy: su Vercel ogni richiesta è una funzione effimera
cd backend && alembic upgrade head
cd backend && alembic revision --autogenerate -m "descrizione in inglese"
cd backend && alembic downgrade -1

# manutenzione del database — vedi la sezione più sotto.
# ⚠️ backup e restore esistono da M2; gli altri arrivano a M5.
cd backend && python -m scripts.backup                 # esporta tutto in JSON
cd backend && python -m scripts.restore FILE.json      # rimette un backup
cd backend && python -m scripts.doctor                 # controlla lo stato
cd backend && python -m scripts.prune                  # toglie la spazzatura
cd backend && python -m scripts.reset --transactions   # svuota, a livelli
cd backend && python -m scripts.users                  # accessi e sessioni
cd backend && python -m scripts.merge_categories A B   # fonde due categorie
cd backend && python -m scripts.seed_demo              # dati di prova
```

Non lanciare comandi che non sono elencati qui senza chiedere prima.

## Struttura del repository

Questa è la struttura da costruire, non quella che c'è.

```
backend/app/models/     SQLAlchemy
backend/app/schemas/    Pydantic, input e output delle API
backend/app/api/        router HTTP: auth, accounts, categories, transactions, stats
backend/app/domain/     logica di business pura (money, period, balances, stats)
backend/migrations/     Alembic
backend/scripts/        manutenzione del database, da lanciare a mano
backend/tests/          pytest, concentrati su domain/
frontend/src/features/  una cartella per area: dashboard, transactions, accounts,
                        categories, settings
frontend/src/api/       client tipizzato verso il backend + cache delle letture
frontend/src/lib/       helper trasversali (money.ts, period.ts, chart.ts,
                        validation.ts, online.ts, pwa.ts)
frontend/src/components/charts/   i grafici: Recharts spogliata, e il tooltip scritto
frontend/src/styles/    tokens.css (design system) + index.css
frontend/public/        asset serviti tali e quali: icone, manifest, sw.js
api/index.py            entrypoint Vercel, monta l'app FastAPI
requirements.txt        dipendenze Python di runtime (le legge Vercel, sta in root)
vercel.json             build del frontend + routing verso la function Python
docs/plan/              il piano di progetto
docs/design/            DESIGN.md, il design system
docs/mockup/            l'immagine di riferimento da cui è nata la direzione visiva
```

## Il denaro

È la parte in cui un'app di questo tipo sbaglia per sempre e in silenzio, quindi viene
prima di tutto il resto.

⚠️ **Gli importi sono interi in centesimi ovunque: database, API, stato del frontend.**
`amount_cents`, `BigInteger`. Mai un `float`, e nemmeno un `NUMERIC` che poi qualcuno legge
dentro un float da qualche parte lungo il tragitto. In virgola mobile `0.1 + 0.2` fa
`0.30000000000000004`, e su un anno di movimenti diventa un saldo che non torna con la
banca per due centesimi e un pomeriggio buttato a cercare dove.

**Con gli interi il problema smette di esistere lungo tutto il percorso.** Un intero
attraversa JSON senza perdere niente e resta esatto anche in JavaScript, dove i numeri sono
sì float64 ma rappresentano gli interi esattamente fino a 2^53 — in centesimi, novantamila
miliardi di euro. Quindi **il frontend può sommare**, e lo fa: totali di una selezione,
percentuali di una fetta, differenze fra due periodi si calcolano dove servono, senza dover
chiedere al server un numero che è una somma di dati che ha già in mano.

⚠️ **Il frontend somma, ma non decide cosa sommare.** L'aritmetica è aritmetica; la regola
"un trasferimento non è una spesa" resta del dominio, arriva già applicata nei dati o nei
campi che il server espone, e non si riscrive in un componente. La riga da non passare non
è la somma, è la classificazione.

⚠️ **La parola "centesimi" non deve mai arrivare all'utente.** È una rappresentazione
interna e basta: si scrive `12,50` e si legge `12,50 €`, in ogni campo, ogni etichetta,
ogni messaggio di errore, ogni esportazione. Le due conversioni vivono in `domain/money.py`
e in `frontend/src/lib/money.ts`, e da nessun'altra parte.

⚠️ **La divisione per 100 avviene solo dentro il formattatore.** Nel momento in cui dividi
ottieni un float e hai buttato via la ragione per cui usavi gli interi. Si somma in
centesimi, si confronta in centesimi, si ordina in centesimi: `formatMoney(cents)` è l'unico
punto che produce una stringa in euro, ed è l'ultimo passo prima dello schermo.

⚠️ **E il parsing non è `parseFloat(testo) * 100`.** `19.99 * 100` in virgola mobile fa
`1998.9999999999998`: troncato diventa `19,98`, cioè un centesimo perso su una buona parte
degli importi che scriverai. La conversione lavora sulle **cifre** — parte intera e parte
decimale separate dal separatore, decimali riempiti o troncati a due, poi concatenate — e
non passa mai da un numero con la virgola. È il bug classico di questo modello e merita un
test suo.

**Un effetto collaterale che vale la pena avere**: un intero si comporta allo stesso modo su
Postgres e su SQLite, quindi la suite di test non può passare mentendo su una precisione che
in produzione non c'è. Con i decimali sarebbe successo: SQLite non ha un tipo decimale
nativo e SQLAlchemy ripiega sui float.

⚠️ **Quando un importo si spezza in parti** — le percentuali di una torta, una media, una
divisione — **il resto va sull'ultima parte**. Arrotondando ogni pezzo per conto suo la somma
delle fette non fa più il totale, e in un grafico si vede a occhio.

⚠️ **L'importo è sempre positivo, il segno lo porta il `kind`.** Un movimento è `expense`,
`income` o `transfer`; non esiste un importo negativo. Se il segno stesse nell'importo,
ogni somma della codebase avrebbe un `abs()` da ricordare, e prima o poi ci sarebbe un
`-0` da qualche parte. Il segno è una proprietà del *tipo* di movimento, non del numero.

⚠️ **Un movimento ha una data, non un istante.** Colonna `date`, non `timestamp`: una spesa
è "il 12 marzo", e trasformarla in un istante significa portarsi dietro i fusi orari in
un'app che gira su un telefono in viaggio, con il risultato che una spesa di mezzanotte
finisce nel mese sbagliato. `created_at` esiste, è un timestamp, ed è metadato: non entra
mai in un raggruppamento per periodo.

**La formattazione e il parsing stanno in un posto solo**: `domain/money.py` lato server e
`frontend/src/lib/money.ts` lato client, che ne è lo specchio. Italiano: separatore
migliaia `.`, decimale `,`, simbolo dopo con lo spazio — `1.234,56 €`. Il parsing accetta
quello che una persona scrive davvero: `12,50`, `12.50`, `1.234,56`, con o senza spazi.

⚠️ **Mai `type="number"` legato a `Number(event.target.value)`.** Svuotando la casella il
valore diventa `0` e si riempie da sola, quindi si può cambiare solo con le frecce; e con
la virgola decimale italiana il campo numerico del browser si comporta in modo diverso a
seconda della lingua del sistema. Il valore si tiene **come stringa** mentre lo scrivi, si
valida a parte con `parseAmountField`, e diventa un intero in centesimi **solo al
salvataggio**, con la conversione a cifre descritta sopra. Il vuoto si segnala, non si
corregge: **stringa vuota è un errore, non zero.**

## I conti e i saldi

Un conto (`account`) è un posto dove stanno dei soldi: conto corrente, conto deposito,
contante, prepagata. Ha un `opening_balance_cents` e una `opening_date` — il punto da cui
inizi a tenerne traccia.

⚠️ **Il saldo non è una colonna, è una somma.** `saldo = opening_balance + Σ movimenti`,
sempre, calcolato in `domain/balances.py`. Tenere anche una colonna `balance` da aggiornare
a ogni scrittura significa avere due numeri che possono contraddirsi, e quando lo faranno
non saprai quale dei due credere. Il calcolo costa una somma su qualche migliaio di righe:
niente.

⚠️ **In V1 tutti i conti sono immediati.** Nessun addebito differito, nessun estratto conto
della carta. Una carta di credito, se servirà, si modella come un conto normale che va in
negativo e che azzeri a fine mese con un trasferimento dal conto corrente: il caso è
rappresentabile senza aggiungere un concetto.

**`include_in_net_worth`** esiste perché non tutto quello che vuoi tracciare è tuo
patrimonio (un conto cointestato, dei soldi che stai tenendo per qualcun altro). Sta sul
conto, di default è vero, e influenza **solo** il totale del patrimonio: i movimenti di
quel conto restano nelle statistiche di spesa.

⚠️ **I conti si archiviano, non si cancellano.** Un conto estinto ha ancora dentro la
storia dei tuoi movimenti, e il grafico del patrimonio del 2025 lo attraversa. Archiviato
vuol dire: sparisce dai menù di scelta, resta nella storia.

### La riconciliazione

Prima o poi il saldo dell'app e quello della banca non coincideranno, perché una spesa non
l'hai registrata. Il gesto è "**il saldo vero oggi è X**".

⚠️ **La riconciliazione è un movimento, non una scrittura sul saldo.** L'app calcola la
differenza fra quello che pensa e quello che le hai detto, e registra un movimento
`is_adjustment` di quella differenza — `expense` se eri in meno, `income` se eri in più. Il
saldo resta sempre e solo `opening_balance + Σ movimenti`: una fonte di verità, non due.

⚠️ **Una rettifica muove il saldo e il patrimonio, e non muove le statistiche di spesa.**
Non è consumo, è la misura di quanto ti eri dimenticato: metterla in "uscite per categoria"
inventerebbe una spesa che non sai dove sia andata, e falsare la torta è peggio che
ammettere il buco. Ha `category_id` nullo e viene esclusa da ogni aggregazione di spesa;
nell'elenco dei movimenti si vede eccome, distinta dalle altre.

Se le rettifiche diventano grosse e frequenti, non è un problema dell'app: è il segnale che
stai smettendo di registrare le spese. L'app deve dirlo, non nasconderlo.

## Le categorie

Elenco **libero e a un solo livello**, che gestisci tu: nome, colore, icona, posizione.
Niente sottocategorie — sono la cosa che sembra ordinata il primo giorno e che dopo tre
mesi ti fa esitare fra "Cibo > Spesa" e "Casa > Spesa" ogni volta che registri.

⚠️ **Due elenchi separati, uno per le uscite e uno per le entrate** (`kind` `expense` /
`income`). "Stipendio" non deve comparire fra le categorie di spesa, e un grafico non deve
poter mescolare le due liste. Il nome è unico per household e per segno, **senza distinzione
di maiuscole**, con un indice sul database a garantirlo.

⚠️ **Le categorie si archiviano, non si cancellano.** I movimenti passati le referenziano, e
i confronti mese su mese e anno su anno le leggono: cancellare la riga porterebbe via anche
la storia. Archiviata vuol dire: non si può più scegliere, continua a comparire nei grafici
del passato.

**Un trasferimento non ha categoria**, e non è una dimenticanza: vedi sotto.

**Rinominare una categoria si propaga** ovunque, perché il nome sta sulla categoria e non è
copiato nei movimenti. Fondere due categorie doppione l'app non lo sa fare: c'è lo script
`merge_categories`.

## I movimenti

Tre tipi, una tabella sola:

| `kind` | Cosa | Campi |
|---|---|---|
| `expense` | soldi che escono | `account_id`, `category_id` |
| `income` | soldi che entrano | `account_id`, `category_id` |
| `transfer` | soldi che si spostano | `account_id` (da), `counter_account_id` (a), **nessuna categoria** |

⚠️ **Un trasferimento è una riga sola, non due.** La partita doppia — una riga in uscita sul
conto A e una in entrata sul conto B — è la scelta "corretta" da manuale di contabilità, e
qui è quella sbagliata: raddoppierebbe le righe di ogni elenco, obbligando ogni schermata e
ogni statistica a filtrarne metà, e basta dimenticarsene una volta perché lo stipendio
spostato sul deposito diventi un'entrata da 1.800 €. Con una riga sola e due colonne, **"un
trasferimento non è una spesa" è una verità strutturale** e non una regola da ricordare.

⚠️ **I trasferimenti non entrano mai in entrate, uscite, risparmio o patrimonio.** Spostare
soldi da un conto all'altro non cambia quanto ne hai: i due conti si muovono in direzioni
opposte e il totale resta identico. È **l'errore che rende inutile un cruscotto di finanza
personale**, perché lo stipendio che smisti fra tre conti si presenterebbe come tre entrate
e tre uscite, e ogni numero della dashboard sarebbe gonfio a caso. Il test che lo dimostra è
quello che non si tocca.

Un trasferimento non può avere lo stesso conto da entrambe le parti, e un `CHECK` sul
database lo garantisce insieme alla regola "categoria se e solo se non è un trasferimento".

**L'inserimento rapido** è la schermata più importante dell'app: importo, categoria, salva.
Il conto è preselezionato sull'ultimo usato, la data su oggi, la descrizione è facoltativa.
Tutto il resto (cambiare conto, retrodatare, aggiungere una nota) è raggiungibile ma non è
sulla strada.

⚠️ **La descrizione è facoltativa e resta tale.** Renderla obbligatoria "per avere dati
migliori" è esattamente il campo che a marzo ti fa dire "poi la metto" e ad aprile ti fa
smettere.

⚠️ **La categoria che manca si crea dentro il foglio dell'inserimento**, chiedendo solo il
nome: colore e icona li assegna il server (il colore meno usato della palette, icona
neutra) e si cambiano dopo in Categorie. Mandare qualcuno in un'altra sezione a metà di un
inserimento è il modo migliore per fargli scegliere "Altro" per sempre. È la scelta opposta
al reparto di un ingrediente nel progetto sorgente, e la differenza è che lì indovinare ti
mandava dalla parte sbagliata del negozio, qui un'icona provvisoria non sposta nessun
numero.

⚠️ **I movimenti si cancellano davvero**, a differenza di conti e categorie. Un conto
archiviato è storia; un movimento sbagliato non è storia, è un errore di battitura, e
tenerlo "archiviato" vorrebbe dire falsare ogni totale per sempre.

⚠️ **Le date future sono permesse e contano subito nel saldo.** Il numero risponde a
"quanto mi resterà", non a "quanto ho in questo istante", e finché quei movimenti non
avvengono **non coincide con la banca**. È il compromesso accettato, con una sola
eccezione obbligatoria: **la riconciliazione confronta solo fino a oggi** (`as_of` in
`domain/balances.py`). Un estratto conto non può contenere domani, e senza quel taglio la
differenza includerebbe l'affitto della settimana prossima — generando una rettifica per
soldi che non si sono mossi, che poi resta in archivio per sempre.

## I periodi e le statistiche

**Il periodo di default è il mese solare**, dal primo all'ultimo giorno. I grafici però
accettano un intervallo qualsiasi — ultimi 30 giorni, trimestre, anno, da–a — e il confronto
naturale è **col periodo precedente della stessa lunghezza**.

⚠️ **L'aritmetica sulle date sta in un posto solo**: `backend/app/domain/period.py` e il suo
specchio `frontend/src/lib/period.ts`. Inizio e fine di un mese, periodo precedente, elenco
dei mesi fra due date, etichette ("marzo 2026"). Non fare calcoli di date altrove: è il tipo
di codice che diverge in silenzio, e quando diverge un movimento del 31 finisce in due mesi
o in nessuno.

**Cosa entra in cosa** — da tenere in un punto solo del dominio, perché è la definizione su
cui poggia ogni numero mostrato:

| Numero | Include | Esclude |
|---|---|---|
| Uscite del periodo | `expense` | trasferimenti, rettifiche |
| Entrate del periodo | `income` | trasferimenti, rettifiche |
| Risparmio del periodo | entrate − uscite | trasferimenti, rettifiche |
| Saldo di un conto | tutto ciò che tocca quel conto, rettifiche comprese | niente |
| Patrimonio | somma dei saldi dei conti con `include_in_net_worth` | niente |

⚠️ **Questa tabella è `backend/app/domain/stats.py`**, e non è una parafrasi: le due
funzioni `is_spend` e `is_income` in cima al modulo sono la regola, e ogni numero mostrato
dai due cruscotti esce da lì. `api/stats.py` carica i movimenti una volta e non decide
niente. Il patrimonio a fine mese lo calcola **chiamando** `balances.net_worth(as_of=…)`,
non risommando: una formula, un posto.

⚠️ **Le percentuali viaggiano in millesimi interi** (`share_permille`, 0–1000) e la
divisione avviene nel formattatore, come per i soldi. Il resto va sull'ultima fetta con
qualcosa dentro, così le quote sommano esattamente a 1000: fette che fanno 99,7 % accanto a
un grafico si vedono.

⚠️ **Ogni risposta porta un conteggio dei movimenti**, non solo i totali. È quello che
permette allo schermo di distinguere "non hai speso niente" da "non hai registrato niente",
e la seconda si scrive a parole.

⚠️ **Le aggregazioni si fanno in Python, non in SQL**, e questa è una scelta di scala
dichiarata. Il vincolo architetturale del progetto è che `domain/` non importi nulla di
SQLAlchemy: il router carica i movimenti del periodo, `domain/stats.py` li somma. Un anno di
uso reale sono circa 1.500 movimenti, cinque anni 7.500: sommarli in memoria costa
millisecondi, e in cambio ogni regola di cosa-conta-e-cosa-no è una funzione pura che si
testa senza alzare un database. Questo non vieta al frontend di fare aritmetica sui dati che
ha già — sono interi, sommarli è esatto: vieta di **ridefinire lì** cosa conta come spesa.

**Dove smette di valere**: oltre le decine di migliaia di righe l'aggregazione va spostata in
SQL. Quando succederà, la definizione della tabella qui sopra deve restare in un posto solo —
altrimenti "spesa del mese" comincia a significare due cose leggermente diverse a seconda di
chi la chiede, che è il modo peggiore in cui questo genere di app si rompe.

⚠️ **La paginazione dei movimenti invece è vera da subito.** L'elenco cresce per sempre, e si
pagina con un **keyset** su `(date DESC, id DESC)`, non con `OFFSET`: registrare una spesa di
un mese fa farebbe scorrere tutte le pagine successive sotto le dita di chi sta leggendo, con
righe che si ripetono e righe che spariscono.

## I grafici

**Recharts è approvata** ed è l'unica dipendenza nuova rispetto allo stack di partenza. Due
vincoli d'uso:

- ⚠️ **I colori escono solo dai token del design system.** Nessuna palette di default,
  nessun colore scritto nel componente. Le sei serie sono token come tutti gli altri
  (`--color-chart-1` … `-6`), più `--color-chart-grid` e `--color-chart-axis`.
- **La libreria si ridisegna, non si usa com'è.** Griglie, assi, tooltip e legende di default
  hanno un aspetto suo che non c'entrerà niente col resto dell'app: vanno spogliati fino a
  somigliare al design system, non il contrario.

**Cosa mostra la V1** (dettaglio e motivazioni in `docs/plan/plan-v1.md`): saldi per conto
con totale e ultimi movimenti, uscite per categoria nel periodo (anello + elenco), andamento
entrate/uscite/differenza mese per mese, patrimonio a fine mese, confronto col periodo
precedente, le cinque uscite più grandi, spesa media giornaliera con proiezione a fine mese.

⚠️ **I periodi dell'analisi sono solari e sono solo quelli che hanno dati.** L'anno è
gennaio–dicembre e il trimestre è uno dei quattro fissi, non "gli ultimi dodici o tre mesi":
una finestra mobile vuol dire una cosa diversa ogni volta che la apri, e due letture a una
settimana di distanza non sono confrontabili. E il selettore offre **solo i periodi in cui
hai registrato qualcosa** (`GET /api/stats/calendar`): proporre marzo 2019 e poi spiegare
sette volte che non c'è niente fa sembrare rotta la schermata. L'unico posto in cui un
periodo vuoto si può scegliere è l'intervallo libero da–a, perché quelle due date le hai
scritte tu.

⚠️ **Ogni grafico è un punto di partenza, non un quadro.** Da una fetta della torta si deve
poter scendere ai movimenti che la compongono: un numero che non si può aprire è un numero di
cui non ti fiderai, e il primo istinto davanti a "Trasporti 340 €" è "e da dove esce?".

⚠️ **Un periodo senza dati si dice, non si disegna.** Un grafico vuoto con gli assi a zero si
legge come "hai speso zero", che è diverso da "non hai registrato niente".

## Design

Il design system è **concluso** e vive in [`docs/design/DESIGN.md`](docs/design/DESIGN.md).
È la fonte di verità per palette, tipografia, forme, iconografia e tono di voce: non
inventare stili, non introdurre colori o componenti che non stanno lì.

Direzione: **cruscotto notturno**. Scuro, calmo, denso di numeri, un solo colore che
brilla. I token sono travasati in `frontend/src/styles/tokens.css` (blocco `@theme` di
**Tailwind 4**; niente `tailwind.config.js`, in Tailwind 4 non esiste), definiti una volta
sola. Nei componenti solo classi Tailwind: **nessun valore arbitrario sparso**. Se serve un
colore o una spaziatura che non è un token, prima si aggiunge a DESIGN.md.

I punti su cui si sbaglia più facilmente:

- **Tema solo scuro in V1.** Non esiste una variante chiara e non va aggiunta di
  iniziativa. `color-scheme: dark` e il `theme-color` della pagina fanno parte del tema:
  senza, la barra del browser su telefono resta bianca sopra una pagina nera.
- **Verde `#3DF29B` è l'unico accento**, e il **glow** è riservato all'azione primaria e al
  FAB. Non si spalma.
- **Massimo due colori di sfondo per schermata**: `--bg-app` per la pagina, `--surface-card`
  per le card. Bordi hairline in verde-alpha, mai grigi esadecimali.
- ⚠️ **I quattro colori del denaro non sono decorativi, sono semantica**: entrate verdi col
  `+`, uscite rosse col `−`, **trasferimenti ciano e senza segno**, rettifiche ocra. Il
  ciano esiste perché un trasferimento non è né un'entrata né un'uscita: se la sua riga si
  legge come una spesa, tutto il senso del modello si perde nell'unico posto in cui l'utente
  guarda.
- **Tutti i numeri sono Space Grotesk con `tnum` e `lnum`**, allineati a destra, sempre
  nella stessa posizione. È quello che fa leggere una colonna di importi invece di farla
  ballare. C'è la classe `.num` in `styles/index.css`.
- **Icone: Lucide**, stroke 2px, 20–24px. Niente emoji, niente unicode come icone, **niente
  SVG disegnati a mano** — è la scelta opposta a quella dell'altro progetto, ed è
  deliberata. Trasferimenti: `arrow-left-right` in contenitore quadrato, categorie in
  contenitore rotondo.
- **Nessun logo**: wordmark tipografico "Wallet." in Space Grotesk 600 con il punto finale
  in accento, reso sempre come testo (`components/Wordmark.tsx`).
- **Movimento**: 120/200 ms su `cubic-bezier(.2,.8,.2,1)`, fogli che salgono dal basso.
  Niente bounce, niente parallax.
- **Copy in italiano, sentence case**, seconda persona informale, niente emoji. Numeri con
  virgola decimale e simbolo dopo con lo spazio: `1.234,56 €`.
- **Navigazione**: cinque sezioni — **Riepilogo, Movimenti, Conti, Categorie, Analisi** —
  nella tab bar mobile a sole icone, e le stesse nella sidebar su desktop.
- ⚠️ **Il profilo non è una sezione.** Su telefono è un bottone fisso in alto a destra,
  nella testata insieme al wordmark; su desktop è la sesta voce della sidebar, in fondo.
  **Una strada sola per piattaforma**: mai tutte e due insieme.
- **Le categorie sono una sezione a sé**, non un angolo delle impostazioni: qui c'era
  scritto "le tocchi due volte l'anno", che è vero a regime e falso proprio quando le stai
  configurando.

⚠️ **Il bottone "+" non è una scheda, ed è deliberato.** DESIGN.md lo disegnava al centro di
una barra da quattro; dando al profilo la quinta scheda il centro non esiste più, quindi
**fluttua in basso a destra, sopra la barra**. Il principio non cambia — l'inserimento di un
movimento è l'unica azione con un posto fisso sullo schermo, perché è quella che si fa in
piedi alla cassa e che decide se l'app viene usata o abbandonata. Cambia solo dove quel
posto sta. Lo scostamento è registrato in DESIGN.md, non lasciato al codice.

⚠️ **I riferimenti in fondo a DESIGN.md non esistono nel repository.** `tokens/`,
`guidelines/`, `components/`, `ui_kits/wallet-app/`: è arrivato solo il documento. Non dare
per scontato che quei file ci siano.

⚠️ **`docs/mockup/` non contiene un mockup di Wallet**: è il cruscotto di un altro prodotto,
la fonte della direzione visiva. Si guarda per l'aria che deve avere il prodotto, non per
copiarne le schermate.

## Pagina di diagnostica

`/_stato` mostra lo stato di frontend, API e database, più i token del design system. Non è
linkata da nessuna parte nell'app: ci si arriva solo digitando l'URL.

**Sta fuori dal login di proposito.** Accedere richiede il database, quindi metterla dietro
la sessione la renderebbe irraggiungibile proprio quando il database è la cosa rotta. Il
rischio di divulgazione si chiude a monte: `/api/health` deve restituire `detail` **solo
quando qualcosa non va**, così a sistema sano non pubblica la versione di Postgres.

⚠️ E qui, a maggior ragione, **non deve mai comparire un dato di dominio**: niente conteggi
di movimenti, niente saldi, niente nomi di conti.

## PWA

L'app si installa sulla home e parte a schermo pieno. I pezzi stanno in `frontend/public/`:
`manifest.webmanifest`, le icone, e `sw.js`.

**Il service worker si scrive a mano**, non con `vite-plugin-pwa`: sono un centinaio di righe
commenti compresi, e la libreria porterebbe Workbox più un'integrazione col build per
risolvere problemi che qui non ci sono. Se un giorno servono precache manifest e prompt di
aggiornamento, quel file si butta e si prende la libreria.

Le strategie sono per tipo di risorsa, e una di queste è "nessuna":

| Cosa | Strategia |
|---|---|
| **`/api/*`** | **mai toccato** |
| navigazioni | rete, poi la shell dalla cache |
| `/assets/*` | cache, poi rete — Vite ci mette l'hash nel nome |
| icone, manifest, font | dalla cache e aggiornati dietro |

⚠️ **`/api` è escluso di proposito e non va incluso.** Sono risposte autenticate e sempre
fresche; qui sono anche il quadro completo delle tue finanze. Metterle in una cache che
sopravvive al logout significherebbe servire i saldi di una sessione chiusa a chi apre l'app
dopo. La cache delle letture c'è già, sta in `api/cache.ts`, ed è **in memoria** — muore con
la pagina, che è esattamente quello che si vuole.

⚠️ **Offline non è un obiettivo, e l'inserimento offline nemmeno.** È stato valutato e
scartato per la V1: una coda locale di movimenti da spedire quando torna la rete è il pezzo
più delicato di tutto il progetto (duplicati, conflitti, righe che non si possono modificare
finché non hanno un id) e non si costruisce prima che l'app esista. Il service worker serve
la shell così l'app si apre invece di dare l'errore del browser, e `lib/online.ts` alza una
fascia che dice che sei senza rete.

Il service worker **si registra solo in produzione** (`import.meta.env.PROD` in `main.tsx`):
in sviluppo servirebbe il bundle di ieri e ogni modifica sembrerebbe non applicata.

**Su iOS i meta contano ancora**: `apple-mobile-web-app-capable` è ciò che fa partire davvero
a schermo pieno, il `display` del manifest non basta. Status bar `default`, non
`black-translucent`, altrimenti il contenuto finisce sotto l'orologio.

⚠️ **Il campo "incolla il link" nella schermata di accesso serve solo in standalone.** Su iOS
un'app aggiunta alla home ha uno spazio dati separato da Safari: il magic link apre Safari, la
sessione nasce lì, e l'app installata resta scollegata — senza barra degli indirizzi da cui
rimediare. Il campo spende il token dentro l'app. In una scheda del browser toccare il link
funziona, quindi lì il campo non compare: il riconoscimento sta in `lib/pwa.ts`. Il
copia-invece-di-aprire non è negoziabile: il token si usa una volta sola e chi lo tocca primo
vince.

## Autenticazione

Magic link, nessuna password. Le regole da non violare:

- **`/request-link` risponde sempre allo stesso modo.** Dire a un indirizzo che non è
  abilitato trasformerebbe l'endpoint in un modo per scoprire chi ha accesso. Solo i log
  distinguono i casi.
- **`/verify` è una POST, mai una GET.** I provider di posta aprono i link per analizzarli:
  con una GET uno scanner brucerebbe il token monouso prima del destinatario. Il link porta a
  una pagina che fa la POST via JavaScript, che gli scanner non eseguono.
- **I token non si salvano mai in chiaro**, solo il loro SHA-256. Vale per i link e per le
  sessioni.
- **La sessione è un token opaco**, non un JWT: revocarla è un `UPDATE`, e "esci da tutti i
  dispositivi" è lo stesso `UPDATE` senza filtro sull'id.
- **Chi può entrare** sta in `ALLOWED_EMAILS`. Al primo accesso l'utente entra nell'unico
  household, seminato dalla migrazione iniziale.
- La tabella si chiama `app_user` e non `user` perché `user` è una parola riservata di
  Postgres e andrebbe messa fra virgolette a ogni query.

### La sessione lunga, e perché qui va motivata meglio

Trenta giorni sono una scelta di comodità: l'app si apre più volte al giorno da un telefono, e
un login a ogni apertura la ucciderebbe. Ma **il rischio va detto per quello che è**: questo
database contiene il quadro completo delle finanze di una persona — dove ha i soldi, quanti
sono, e cosa compra. Non è un dato come un altro.

Il rischio accettato è "qualcuno con il telefono sbloccato in mano apre l'app", lo stesso di
un'app bancaria lasciata aperta. Quello che **non** è accettato, e quindi è obbligatorio:

- cookie `httpOnly` + `Secure` + `SameSite`, mai il token in `localStorage`;
- link di accesso **monouso e valido 15 minuti** — quello vive in una casella email, ed è
  l'anello debole vero;
- refresh scorrevole della sessione a ogni uso, così i 30 giorni contano dall'ultimo uso e non
  dal login;
- **"esci da tutti i dispositivi"** raggiungibile in due tocchi dal profilo, non nascosto;
- nessun importo, nessun saldo e nessun indirizzo email nei log.

Se un giorno la superficie non basterà, la mossa non è accorciare la sessione: è un blocco
locale (PIN o biometria) davanti all'apertura dell'app. Non è in V1.

## Proprietà dell'utente

Due categorie, con criteri diversi su dove metterle:

- **Colonna vera** per ciò che si mostra, si ordina o si cerca: `display_name` sta qui. Il
  fallback "nome, altrimenti email" vive lato server nella proprietà `User.label` ed è esposto
  nell'API come campo `label`, così la regola non viene riscritta in ogni componente e non può
  divergere.
- **`preferences`, campo JSON** per le impostazioni di interfaccia: cambiano spesso, si
  leggono sempre in blocco e non si interrogano mai per chiave, quindi una colonna ciascuna
  significherebbe una migrazione per ogni casella di spunta. La forma è comunque validata da
  `schemas/user.UserPreferences`: aggiungere una preferenza è **un campo tipizzato in quella
  classe, senza migrazione**.

`UserPreferences` accetta chiavi sconosciute di proposito: un frontend più recente può salvare
un'impostazione prima che il backend la dichiari, e un rollback non cancella in silenzio
quello che avevi impostato. La `PATCH /api/auth/me` **fonde** le preferenze invece di
sostituirle.

⚠️ **Le impostazioni che riguardano i soldi non vanno qui.** L'obiettivo di risparmio mensile,
il conto preselezionato, la valuta: sono proprietà dell'**household**, non della persona.
`preferences` è personale, e il giorno in cui l'app diventa condivisa una preferenza personale
non deve poter cambiare i numeri che vede l'altro.

**L'obiettivo di risparmio** è un campo su `household` (`monthly_savings_target_cents`),
letto e scritto da `GET` / `PATCH /api/household` — che è anche dove finiranno il conto
preselezionato e la valuta. ⚠️ **`null` vuol dire "non me lo sono dato", e non è zero**: un
obiettivo a zero mostrerebbe una barra piena per il motivo sbagliato, e un'app che si
inventa un obiettivo che non hai scelto ha cominciato a dare consigli. Si modifica dal
Riepilogo, dove lo guardi, non da un pannello di impostazioni: un obiettivo si tara
guardando i mesi che hai avuto davvero.

Non è una tabella: c'è un valore solo e i periodi passati si confrontano con quello corrente.

### ⚠️ Il ciclo dello stipendio

**L'obiettivo non si giudica sul mese solare, si giudica da uno stipendio al successivo.**
I soldi arrivano il 27, non il primo, e la domanda vera è se lo stipendio di novembre era
ancora lì quando è arrivato quello di dicembre. Il confine del mese taglia quella tratta a
metà e risponde a una domanda che nessuno ha fatto.

- **Un ciclo parte dal primo stipendio di ogni mese solare**; altri pagamenti dello stesso
  mese si **sommano** a quel ciclo. È ciò che impedisce alla tredicesima di spezzare
  dicembre in due cicli, uno dei quali lungo cinque giorni con sopra un verdetto sul
  risparmio.
- **Uno stipendio è un'entrata nella categoria che hai indicato tu**
  (`household.salary_category_id`). ⚠️ Non "una qualsiasi entrata" — un rimborso da 10 €
  aprirebbe un ciclo — e non "l'entrata più grande del mese", che è una regola che indovina
  e che il mese in cui vendi qualcosa di costoso sposta i confini senza dirtelo. Se non
  l'hai scelta, la schermata te lo chiede invece di supporre.
- **Il verdetto è sul ciclo chiuso**, quello che un nuovo stipendio ha già terminato: è
  l'unica tratta la cui spesa è finita. Obiettivo raggiunto se
  `stipendio − speso ≥ obiettivo`.
- **Il ciclo in corso non ha un verdetto, ha un residuo**: `stipendio − speso − obiettivo`,
  cioè quanto puoi ancora spendere prima del prossimo stipendio. È l'unico numero della
  dashboard su cui puoi ancora agire. Negativo vuol dire che l'obiettivo è già fuori
  portata, e si mostra quanto.
- ⚠️ **La fine del ciclo in corso è oggi**, perché nessuno sa quando arriva il prossimo
  stipendio. È l'unico confine onesto disponibile, ed è anche il motivo per cui quel ciclo
  non può avere un verdetto.
- **Quello che spendi prima del primo stipendio in assoluto non sta in nessun ciclo**: non
  c'è uno stipendio da cui sia uscito, quindi non c'è niente contro cui giudicarlo. È una
semplificazione consapevole — se un giorno servirà la storia dell'obiettivo diventa una
tabella con `valid_from`, e i mesi passati smetteranno di cambiare valutazione ogni volta che
alzi l'asticella.

## Vocabolari chiusi

Stanno in `backend/app/domain/vocabulary.py` e sono rispecchiati in
`frontend/src/api/client.ts`. Sono chiusi perché sono **struttura**, non contenuto:
aggiungere un valore richiede di decidere cosa fa il resto del codice quando lo incontra.

- **Tipo di movimento**: `expense`, `income`, `transfer`
- **Tipo di conto**: corrente, deposito, contante, prepagata
- **Tipo di categoria**: `expense`, `income`

⚠️ **Le categorie invece sono aperte** e le gestisci tu: sono contenuto. Non metterle qui, non
seminarle nel codice, non trattarle come un enum.

## Manutenzione del database

Stanno in `backend/scripts/`, si lanciano con `python -m scripts.<nome>`, e servono a non
dover entrare a mano nella console di Neon — che è il posto con meno rete di sicurezza per
fare l'operazione più delicata.

**Tutti gli script distruttivi sono una prova a vuoto per default**: stampano cosa farebbero e
non scrivono niente finché non aggiungi `--apply`. Tutti dicono a quale database stanno
parlando prima di fare qualsiasi cosa. `reset --all` e `restore` chiedono in più di scrivere
il nome dell'household.

| Script | A cosa serve |
|---|---|
| `backup` | esporta tutto in JSON. **Il più importante di tutti**, vedi sotto |
| `doctor` | ⚠️ **prima di tutto: la migrazione applicata è quella del repository?** Poi movimenti orfani, trasferimenti rotti, importi a zero, categorie di segno sbagliato, doppioni probabili |
| `restore` | rimette un backup. **Solo in sostituzione**, mai in fusione |
| `prune` | token e sessioni morti, categorie e conti archiviati che non usa più nessuno |
| `reset` | svuota a livelli: `--transactions`, `--categories`, `--accounts`, `--all` |
| `users` | chi ha accesso, e revoca delle sessioni |
| `merge_categories` | fonde due categorie che sono la stessa cosa |
| `seed_demo` | qualche mese di movimenti finti, per avere grafici da guardare mentre li costruisci |

⚠️ **`backup` qui vale più che in qualsiasi altro progetto.** Non è "dati inseriti a mano che
sarebbe noioso rifare": **le spese di marzo non si ricostruiscono**. Non esistono da
nessun'altra parte se non, parzialmente, in un estratto conto che l'app non sa leggere. Il
free tier di Neon non conserva backup a lungo. Va lanciato con una cadenza vera, e deve
esistere **da M2**, cioè dal primo momento in cui c'è un dato che vale qualcosa — non alla
fine del progetto.

⚠️ **`backup-*.json` va in `.gitignore`.** Contiene tutti i tuoi movimenti, i saldi e
l'indirizzo email, e il nome di default finisce nella cartella da cui lanci — cioè dentro il
repository.

⚠️ **Le cancellazioni sono esplicite, non affidate ai `CASCADE`.** I test girano su SQLite,
che le foreign key non le applica se non gliel'hai detto, mentre la produzione è Postgres: uno
svuotamento che si appoggiasse al database si comporterebbe diversamente nei due posti.

⚠️ **`reset --accounts` e `reset --categories` tirano dentro i movimenti**, e lo devono dire:
un conto non si può cancellare finché un movimento lo nomina, e un movimento senza conto non
significa niente.

⚠️ **`users` non decide chi può entrare**: quello è `ALLOWED_EMAILS`, che sta nell'ambiente su
Vercel. Cancellare la riga non chiude niente — il prossimo magic link ricrea l'utente.

## Invio email (Brevo)

Tutto passa da `backend/app/mail/sender.py`. Tre cose da non toccare:

- **Lo `user-agent` esplicito è obbligatorio.** Brevo sta dietro Cloudflare, che risponde
  `403 browser_signature_banned` alla firma predefinita di `urllib` (`Python-urllib/3.x`).
  Senza quell'header ogni magic link fallisce in silenzio. Ci vuole un test di regressione
  apposta, perché è un header invisibile e facile da perdere.
- **Chiave API v3** (`xkeysib-`), non quella SMTP (`xsmtpsib-`).
- **`MAIL_FROM` verificato su Brevo.** L'API accetta anche un mittente non verificato senza
  errori, ma poi il messaggio fallisce SPF/DKIM e finisce nello spam: sembra funzionare e non
  arriva.

Se `BREVO_API_KEY` o `MAIL_FROM` sono vuote, il link viene stampato sul terminale invece di
essere inviato: è così che si sviluppa in locale senza account Brevo.

⚠️ **Nell'email non ci va nessun dato finanziario.** Solo il link. Niente saldi, niente
riepiloghi mensili: la posta è il canale meno protetto che tocchi questo sistema.

## Variabili d'ambiente

| Nome | A cosa serve |
|---|---|
| `DATABASE_URL` | Neon, **host pooled** (con `-pooler`) |
| `ENVIRONMENT` | `development` o `production`; regola il flag `Secure` sul cookie |
| `ALLOWED_EMAILS` | indirizzi abilitati, separati da virgola |
| `APP_BASE_URL` | base per costruire il link assoluto nell'email |
| `BREVO_API_KEY` | se vuota, in sviluppo il link finisce sul terminale |
| `MAIL_FROM` | mittente verificato su Brevo |
| `MAIL_FROM_NAME` | `Wallet` |

## Convenzioni di lavoro

- **Pianifica prima di scrivere.** Per qualsiasi task non banale, entra in plan mode, proponi
  un piano, aspetta la mia approvazione.
- **Commit piccoli e atomici**, un cambiamento logico per commit. Messaggi in inglese,
  imperativo ("add transfer endpoint").
- **Non aggiungere dipendenze senza chiedere.** Se serve una libreria, proponila spiegando
  cosa risolve e quali alternative hai scartato. Recharts è l'unica già approvata oltre a
  quelle di base.
- **Non riscrivere codice che non è oggetto del task.** Se noti un problema altrove, segnalalo
  a parole invece di sistemarlo di tua iniziativa.
- **Niente commit automatici**: mostrami il diff, decido io quando committare.
- Se una richiesta è ambigua, fai una domanda invece di scegliere per me.

## Convenzioni di codice

**Dove vive la logica di business.** `backend/app/domain/` non importa **nulla** di FastAPI né
di SQLAlchemy: riceve oggetti semplici e restituisce oggetti semplici. I router in `api/`
traducono HTTP → dominio → HTTP; i modelli SQLAlchemy non contengono logica. È questa
separazione che rende testabile senza database la parte che può davvero sbagliare — somme,
saldi, confini di periodo — ed è il vincolo architetturale più importante del progetto.

Nel frontend vale lo stesso principio: i componenti React non contengono regole di dominio, si
limitano a mostrare ciò che arriva dal backend. **Un componente non decide mai se un movimento
conta come spesa.**

**Naming.** Python `snake_case`, moduli di dominio con il nome della cosa che calcolano
(`money.py`, `period.py`, `balances.py`, `stats.py`). Componenti React in `PascalCase`, un
componente per file. Cartelle di feature al plurale (`features/transactions/`). Nel database:
tabelle al singolare (`account`, `transaction`), chiavi esterne `<tabella>_id`. **Gli importi
portano sempre il suffisso `_cents`** (`amount_cents`, `opening_balance_cents`), in ogni
strato: modello, schema, campo TypeScript. È l'unica cosa che impedisce a un `amount` senza
suffisso di finire in una somma di euro senza che nessuno se ne accorga.

**Lingua.** Codice, nomi e commenti in inglese; testi rivolti all'utente in italiano.

**Errori.** Il dominio solleva eccezioni proprie e i router le traducono in codici HTTP. Mai
`except` silenziosi.

**Validazione e sanitizzazione.** Su due livelli, con ruoli diversi:

- **Backend, sempre e comunque.** Pydantic con vincoli espliciti (`gt=0` sugli importi,
  `min_length`, `max_length`), `extra="forbid"` sugli schemi di scrittura così un campo scritto
  male fallisce a voce alta invece di sparire, e i testi trimmati da un `field_validator`. È
  l'unica autorità: il frontend non è un confine di sicurezza.
- **Frontend, per non far fare sciocchezze all'interfaccia.** Gli helper stanno in
  `frontend/src/lib/validation.ts` e `frontend/src/lib/money.ts`.

Regola generale: l'input dell'utente si accetta come lo scrive e si normalizza al salvataggio.
Non si riscrive sotto le dita di chi sta digitando.

**Test.** Si testa `domain/`, dove sta tutta la logica che può sbagliare: somme in centesimi,
saldi, confini di periodo, aggregazioni, conversione fra testo in euro e centesimi. Non si testano i CRUD banali né
i componenti React. **Obbligatorio e non negoziabile** il test che dimostra che un
trasferimento non compare mai fra entrate o uscite, con nessun raggruppamento e in nessun
periodo. L'elenco completo sta in [`docs/plan/plan-v1.md`](docs/plan/plan-v1.md).

**Dati dal server.** Le letture passano da un `useQuery` in `frontend/src/api/cache.ts`, una
cache stale-while-revalidate scritta a mano: entro una manciata di secondi il dato torna senza
richiesta, oltre torna subito e si aggiorna in silenzio. Le scritture invalidano da sole il
prefisso che toccano, **dentro `api/client.ts`**, così chi chiama non può dimenticarsene. Non
c'è TanStack Query: per una manciata di endpoint sarebbe più configurazione che codice. Se un
giorno servono retry, paginazione condivisa fra componenti o de-duplica, quel file si butta e
si sostituisce con la libreria.

⚠️ **La paginazione dei movimenti è l'eccezione**: quella è una lista che cresce, non una
lettura da rinfrescare. Si tiene per conto suo, con il cursore keyset, e non passa dalla cache
delle letture.

⚠️ **Due chiavi sopravvivono alla chiusura della pagina, e solo due**: `/api/accounts` e
`/api/categories`, in `localStorage` sotto `wallet:cache:`. Sono anagrafiche — un nome, un
colore, un'icona — le legge quasi ogni schermata, e sono ciò che fa aprire il foglio di
inserimento già pieno invece che dopo un giro sul server. La lista è un elenco chiuso in
`api/cache.ts`, non una politica generale.

⚠️ **Dal disco tornano i nomi, non gli importi.** `/api/accounts` porta anche
`balance_cents`, che cambia a ogni movimento: `useQuery` restituisce un `fromDisk`, e finché
è vero le schermate mostrano il nome e **un trattino al posto del numero**. Un saldo di ieri
stampato con sicurezza è il caso peggiore di questo progetto — su un numero mancante indaghi,
di uno sbagliato ti fidi. `/api/stats/*` e i movimenti non vanno su disco per niente.

⚠️ **Il disco si svuota al logout** (`clearCache()`) e quando l'utente è un altro. Vale la
stessa ragione scritta per il service worker: una cache che sopravvive alla sessione
servirebbe i dati di una sessione chiusa a chi apre l'app dopo. Il token di sessione, quello,
resta dove è sempre stato — nel cookie `httpOnly`, mai in `localStorage`.

⚠️ **Attesa visibile: `BusyOverlay` è per le scritture.** Blocca la pagina perché un
salvataggio non si tocchi due volte e perché tu sappia che i soldi sono arrivati.

**Le letture non lo alzano.** Una `GET` è silenziosa per default (`api/client.ts`), e la
regola qui diceva il contrario: *"ogni richiesta in primo piano"*. Era sbagliata, e si è
vista all'uso — ogni apertura dell'app, ogni cambio di periodo, ogni scadenza dei 30 secondi
di freschezza metteva uno scrim a schermo intero, e l'app sembrava lenta. Una lettura non ha
niente da proteggere: se fallisce, lo schermo resta com'era. Bloccare tutto per andare a
prendere un elenco di categorie fa pagare a ogni schermata il prezzo pensato per il gesto che
conta.

**Una schermata che si sta riempiendo lo dice da sé**, con la sua struttura già a posto e i
numeri a trattino (`components/Amount.tsx`), non con uno scrim sopra una pagina bianca.

Le altre due esclusioni restano:

- **I refresh in background della cache non contano.** Bloccare la pagina per un aggiornamento
  che non hai chiesto annullerebbe il senso della cache.
- **Sotto i 200 ms non compare niente.** Un lampo di "Attendi…" su un salvataggio da 60 ms si
  legge come un difetto, non come un riscontro.

⚠️ **Il salvataggio di un movimento aspetta il server, e non è ottimistico.** È la differenza
fra un'app che registra soldi e una che spunta cose da fare: qui una riga che compare
e poi svanisce perché la richiesta è fallita è un movimento che credi registrato e non lo è, e
te ne accorgi a fine mese. Mezzo secondo di attesa vale la certezza. Se la scrittura fallisce,
**il form resta pieno di quello che avevi scritto**: la cosa peggiore che l'app possa fare è
farti riscrivere l'importo.

## Se il progetto usa un LLM

**In V1 non serve**, e non c'è niente da fargli fare: l'inserimento è manuale e le somme sono
somme.

Da rivalutare in **V1.5**, dove il candidato vero è uno solo: **categorizzare automaticamente
le righe di un estratto conto importato**, cioè trasformare `PAGOBANCOMAT 12/03 ESSELUNGA
MILANO` in "Spesa". Anche lì, prima di un modello si prova la cosa banale — una tabella di
regole "se la descrizione contiene X allora categoria Y", che impara dalle tue correzioni —
perché è deterministica, gratuita e per la maggior parte delle righe basta.

Se quel momento arriva, valgono queste regole:

- I prompt vivono in file dedicati e versionati, mai inline sparsi nel codice.
- Le chiamate al modello passano da un unico modulo, così sono facili da loggare, testare e
  sostituire.
- **Nessuna chiave API nel codice o nel frontend.** Solo variabili d'ambiente, chiamate lato
  server. `.env` sempre in `.gitignore`.
- L'output del modello non è mai considerato attendibile: va validato contro uno schema prima
  di essere usato o mostrato.
- Prevedere sempre un fallback per quando la chiamata fallisce o è lenta.
- ⚠️ **Un movimento categorizzato da un modello nasce "da confermare"** e **non entra nei
  grafici** finché non l'hai guardato. Un numero sbagliato con sicurezza in una dashboard è
  peggio di un numero mancante: sul secondo indaghi, del primo ti fidi.
- ⚠️ **Non si mandano a un servizio esterno più dati del necessario.** Per categorizzare serve
  la descrizione della riga, non il saldo del conto né lo storico.

## Cosa non è questa app

**Non è uno strumento di consulenza finanziaria.** Descrive quello che è successo ai tuoi
soldi; non dice dove metterli, non giudica una spesa, non propone obiettivi che non hai
scritto tu. Non esistono messaggi del tipo "stai spendendo troppo in ristoranti": l'app mostra
quanto hai speso in ristoranti, e il giudizio è tuo.

Vale in particolare per la **V2 con gli investimenti**, dove la tentazione è più forte: nessuna
proiezione di rendimento, nessun confronto con un benchmark presentato come voto, nessun
suggerimento di allocazione. **Descrive, non prescrive** — e nella schermata del patrimonio ci
va un disclaimer visibile, non nascosto in un footer.

## Cose da non fare

- Non committare file `.env`, chiavi, backup del database
- Non modificare la configurazione di build/deploy senza chiedere
- Non introdurre pattern architetturali nuovi senza discuterli prima
- Non introdurre servizi a pagamento: l'hosting deve restare interamente gratuito
- Non mettere logica di dominio nei router o nei componenti React
- Non inventare uno stile finché non arriva il design system
- Non usare i `float` per i soldi. Mai.

## Questioni aperte

Chiuse in fase di planning (dettagli in [`docs/plan/plan-v1.md`](docs/plan/plan-v1.md)):

- [x] Stack → identico al progetto sorgente: React/Tailwind + FastAPI + Postgres su Neon,
      hosting Vercel, magic link via Brevo
- [x] Utenti → uno solo oggi, ma `household_id` ovunque dal primo giorno
- [x] Come entrano i movimenti → **solo a mano** in V1; CSV e ricorrenti in V1.5
- [x] Budget → nessun tetto per categoria, solo l'obiettivo di risparmio mensile
- [x] Saldi → derivati dai movimenti, con la riconciliazione come movimento
- [x] Categorie → libere, un livello, elenchi separati per uscite ed entrate
- [x] Periodo → mese solare di default, intervallo libero nei grafici
- [x] Carte di credito → nessun addebito differito in V1
- [x] Mobile → PWA installabile, solo online
- [x] Grafici → Recharts
- [x] Serve un LLM? → no in V1, da rivalutare in V1.5 per l'import
- [x] Investimenti → V2, con il modello già abbozzato nel piano

Ancora aperte, da decidere in corsa:

- [ ] Taratura dell'obiettivo di risparmio, dopo i primi mesi d'uso reale
- [ ] Serviranno mai conti in valuta diversa dall'euro? V1 è solo EUR, e la crypto della V2 si
      valorizza in euro senza che il conto cambi valuta
- [ ] L'elenco dei movimenti va raggruppato per giorno o resta piatto? Si decide a M3,
      guardando quanti movimenti ci sono davvero in una giornata
