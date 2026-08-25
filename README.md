# Wallet

Web app per il controllo della finanza personale: movimenti su più conti, trasferimenti,
categorie, saldi e grafici.

- Convenzioni e regole di dominio: [`CLAUDE.md`](CLAUDE.md)
- Piano di progetto: [`docs/plan/plan-v1.md`](docs/plan/plan-v1.md)
- Design system: `docs/design/DESIGN.md` — **da produrre**

> ⚠️ **Stato: nessuna riga di codice.** Nel repository ci sono solo i tre documenti qui
> sopra. Tutto ciò che segue — comandi, struttura, script, deploy — descrive **come sarà il
> progetto**, non come è adesso: è la sponda contro cui verificare l'implementazione, e va
> riletto e corretto a valle di ogni milestone. Finché M0 non è fatto, nessuno di questi
> comandi funziona.

## Cosa fa

Registri le spese e le entrate sui tuoi conti, sposti i soldi da un conto all'altro, e
l'app ti dice quanto hai, dove finisce e come cambia nel tempo. Si entra con un magic link
via email, senza password. Si installa sulla home del telefono e parte a schermo pieno.

⚠️ **Un trasferimento fra due conti non è né un'entrata né un'uscita**, e non compare in
nessuna statistica di spesa: sposta soldi, non li crea e non li consuma. Se un numero
sembra troppo basso rispetto a quanto è uscito dal conto corrente, quasi sempre è questo.

⚠️ **Gli investimenti non ci sono**: la V1 conosce solo la liquidità sui conti. Crypto, ETF,
BTP e immobili arrivano in V2 — il piano dice come.

C'è anche una pagina di diagnostica su **`/_stato`**, non linkata dall'app e volutamente
fuori dal login: accedere richiede il database, quindi proteggerla la renderebbe
irraggiungibile proprio durante un guasto. Non espone nulla di sensibile — `/api/health`
riporta dettagli solo quando qualcosa non funziona, e nessun dato di dominio in nessun caso.

## Prerequisiti

Python 3.11+, Node 20+, un account Neon e un account Vercel (entrambi free tier).

## Setup locale

### 1. Database su Neon

1. Crea un progetto su [neon.tech](https://neon.tech) (free tier, regione europea).
2. Copia la connection string e assicurati che usi l'**host pooled**, cioè lo stesso
   endpoint con `-pooler` attaccato all'id, prima del primo punto:

   ```
   ep-cool-darkness-12345.eu-central-1.aws.neon.tech          diretta
   ep-cool-darkness-12345-pooler.eu-central-1.aws.neon.tech   pooled  ← questa
   ```

   La dashboard di Neon non sempre lo propone come scelta esplicita: se la stringa che hai
   copiato non contiene `-pooler`, aggiungilo a mano e lascia il resto invariato. L'app gira
   come funzione serverless, quindi il pooling deve farlo pgbouncer.

3. Copia `.env.example` in `backend/.env` e incolla la stringa in `DATABASE_URL`. Compila
   anche `ALLOWED_EMAILS` con il tuo indirizzo. Lascia `BREVO_API_KEY` vuota: in sviluppo il
   link di accesso viene stampato sul terminale di uvicorn invece di essere inviato.

4. Crea le tabelle:

   ```bash
   cd backend && alembic upgrade head
   ```

### 2. Backend

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements-dev.txt

cd backend && uvicorn app.main:app --reload
```

API su http://127.0.0.1:8000 — documentazione interattiva su `/api/docs`.

### 3. Frontend

In un secondo terminale, dalla radice del repository (il frontend è un npm workspace: `npm`
si lancia da qui, non da `frontend/`):

```bash
npm install
npm run dev
```

App su http://localhost:5173. Vite inoltra `/api` a uvicorn, quindi in sviluppo e in
produzione gli URL sono identici.

### 4. Verifica

Apri **http://localhost:5173/_stato**: devi vedere tre righe verdi (frontend, API,
database). Se il database è rosso, la riga sotto riporta l'errore esatto.

Poi prova ad accedere: vai su **http://localhost:5173/accedi**, inserisci l'email che sta in
`ALLOWED_EMAILS`, e **copia il link dal terminale di uvicorn** — in sviluppo non parte
nessuna email. Aprendolo entri, e resti dentro anche dopo un refresh.

```bash
cd backend && pytest
npm run typecheck
```

## Script di manutenzione

Stanno in `backend/scripts/` e servono a fare sul database le cose che l'app non fa —
salvarlo, ripulirlo, controllarlo — **senza entrare a mano nella console di Neon**, che è il
posto con meno rete di sicurezza per l'operazione più delicata.

Si lanciano sempre da `backend/`, con l'ambiente virtuale attivo:

```bash
cd backend
python -m scripts.<nome> [opzioni]
```

Leggono `DATABASE_URL` dalla stessa `backend/.env` dell'app, quindi **puntano al database
che hai configurato lì**. Se `.env` contiene la stringa di produzione, gli script parlano con
la produzione.

### Le tre regole che valgono per tutti

**1. Non fanno niente finché non lo dici.** Ogni script che cancella o modifica è una prova a
vuoto: stampa cosa farebbe e non scrive. Per eseguire davvero serve `--apply`.

```
$ python -m scripts.reset --all

database: ep-shy-dust-b19zhhev-pooler.c-5.eu-central-1.aws.neon.tech / neondb
Svuotamento
PROVA A VUOTO — niente verrà scritto

  cancello 1.284 movimenti
  cancello 14 categorie
  cancello 4 conti

Prova a vuoto: niente è stato scritto.
Per eseguire davvero, aggiungi --apply
```

**2. Dicono sempre a quale database stanno parlando**, in prima riga, host e nome (mai la
password). È la guardia contro l'unico errore che non ha rimedio: essere altrove da dove
credevi.

**3. Le due irreversibili chiedono di scrivere il nome dell'household.** `reset --all` e
`restore` non si accontentano di `--apply`. `--yes` salta la domanda, per quando lo lanci da
uno script.

### Cosa c'è

#### `backup` — esporta tutto

Il più importante di tutti, e in questo progetto più che in qualsiasi altro: **le spese di
marzo non si ricostruiscono**. Non esistono da nessun'altra parte, se non parzialmente in un
estratto conto che l'app non sa leggere. Il free tier di Neon non conserva backup a lungo.

```bash
python -m scripts.backup                          # backup-AAAA-MM-GG.json qui
python -m scripts.backup --out ~/Desktop/wallet.json
```

Sola lettura, quindi non serve `--apply`. Il file contiene conti, categorie, movimenti e
impostazioni, più l'utente (email, nome, preferenze).

⚠️ **Non contiene sessioni né token di accesso**, di proposito: sono segreti, e ripristinarli
vorrebbe dire far rivivere login che erano stati chiusi.

⚠️ **`backup-*.json` è in `.gitignore`.** Contiene tutti i tuoi movimenti, i saldi e il tuo
indirizzo. Se lo rinomini, non chiamarlo in modo che sfugga a quella regola.

**Lancialo con una cadenza vera** — il primo di ogni mese, insieme al giro di controllo dei
saldi. Un backup che esiste solo quando ti ricordi non è un backup.

#### `restore` — rimette un backup

```bash
python -m scripts.restore backup-2026-08-18.json          # prova a vuoto
python -m scripts.restore backup-2026-08-18.json --apply
```

⚠️ **Sostituisce, non fonde.** Svuota i dati e li ricostruisce dal file. Un backup serve a
rialzarsi da un disastro, non a riconciliare due stati — e la riconciliazione è esattamente
dove questo genere di script sbaglia in silenzio, duplicando movimenti.

Gli id dentro il file non valgono niente su un altro database e vengono rimappati tutti;
l'utente si riconosce dall'email.

#### `doctor` — controlla che sia tutto a posto

```bash
python -m scripts.doctor              # sola lettura
python -m scripts.doctor --fix --apply
```

Controlla che la migrazione applicata sia quella del repository, e poi le cose che possono
davvero rompersi in questo dominio:

- movimenti che puntano a un conto o a una categoria che non esiste più;
- trasferimenti senza contro-conto, o con lo stesso conto da entrambe le parti;
- movimenti con importo zero o negativo (non devono esistere: il segno lo porta il tipo);
- una categoria di segno sbagliato rispetto al movimento — una categoria di entrata su una
  spesa;
- un trasferimento con una categoria attaccata;
- categorie che sembrano doppioni ("Bar" e "bar" non possono coesistere, ma "Bar" e
  "Bar e caffè" sì, e quasi sempre sono la stessa cosa).

`--fix` ripara solo quello che si può riparare senza decidere niente; il resto lo riporta e
lo lascia stare. È il primo comando da lanciare quando un saldo non torna.

#### `prune` — toglie la spazzatura

```bash
python -m scripts.prune
python -m scripts.prune --apply
```

Token di accesso usati o scaduti, sessioni morte, categorie e conti archiviati che nessun
movimento nomina più. ⚠️ **I movimenti non li tocca mai**, a nessuna condizione e per nessuna
anzianità: non sono spazzatura, sono l'unico dato che conta.

#### `reset` — riparti pulito, al livello che vuoi

```bash
python -m scripts.reset --transactions   # solo i movimenti
python -m scripts.reset --categories     # categorie (e quindi i movimenti)
python -m scripts.reset --accounts       # conti (e quindi tutto il resto)
python -m scripts.reset --all --apply    # tutto
```

⚠️ **`--categories` e `--accounts` tirano dentro i movimenti**, e lo dicono: un conto non si
può cancellare finché un movimento lo nomina, e un movimento senza conto non significa
niente.

Utente, sessioni e household non li tocca mai: quelli stanno in `users`.

#### `users` — chi ha accesso

```bash
python -m scripts.users                                   # elenco
python -m scripts.users --logout tizio@example.com --apply
python -m scripts.users --logout-all --apply              # telefono perso
python -m scripts.users --forget tizio@example.com --apply
```

⚠️ **Questa tabella non decide chi può entrare**: lo decide `ALLOWED_EMAILS`, che sta nelle
variabili d'ambiente su Vercel. Cancellare la riga non chiude niente, il prossimo magic link
ricrea l'utente. Per chiudere davvero: prima togli l'indirizzo da `ALLOWED_EMAILS`, poi
revoca le sessioni.

`--logout-all` è il comando da lanciare per primo se perdi il telefono.

#### `merge_categories` — fonde due categorie uguali

```bash
python -m scripts.merge_categories "Bar e caffè" "Bar"
python -m scripts.merge_categories "Bar e caffè" "Bar" --apply
```

La prima sparisce, la seconda resta. Sposta tutti i movimenti e poi cancella. L'interfaccia
non sa farlo: sa rinominare una categoria, ma non riconciliarne due. `doctor` è quello che ti
suggerisce i candidati.

⚠️ **Le due categorie devono avere lo stesso segno.** Fondere una categoria di entrata in una
di uscita non è una fusione, è una perdita di dati: lo script si rifiuta.

#### `seed_demo` — dati di prova

```bash
python -m scripts.seed_demo               # qualche mese di movimenti finti
python -m scripts.seed_demo --reset       # svuota prima
```

Serve a costruire i grafici avendo qualcosa da guardare. ⚠️ **Non lanciarlo mai contro il
database di produzione**: mescolare movimenti finti ai tuoi è un danno che si ripara solo con
un restore.

### Il giro completo, se ti serve ripartire da zero

```bash
cd backend
python -m scripts.backup                    # prima il paracadute
python -m scripts.doctor                    # controlla che il backup sia di dati sani
python -m scripts.reset --all --apply       # ti chiede il nome dell'household
python -m scripts.restore backup-....json   # oppure: seed_demo
```

Da fare con il file di backup in mano.

## Deploy su Vercel

1. Pusha il repository su GitHub.
2. Su Vercel: **Add New → Project**, importa il repository e **non toccare** le impostazioni
   di build: le legge da `vercel.json`.

   ⚠️ **La Root Directory deve restare la radice del repository.** È la trappola che ha
   fatto fallire il primo deploy con:

   ```
   No Output Directory named "dist" found after the Build completed.
   ```

   La documentazione dice che `vercel.json` **sovrascrive** le Project Settings, ed è vero
   — ma solo se Vercel lo trova, e lo cerca nella Root Directory. Se quella punta a una
   sottocartella, il file non viene letto affatto: Vercel rileva Vite da
   `frontend/package.json`, applica il suo preset e cerca il `dist` di *quel* preset invece
   del `frontend/dist` che abbiamo scritto noi. Il sintomo sembra un problema di output
   directory e la causa è altrove, che è il motivo per cui costa un pomeriggio.

   In **Settings → Build & Deployment**, Root Directory va lasciata vuota (o `./`).
3. In **Settings → Environment Variables** aggiungi, per tutti e tre gli ambienti:

   | Nome | Valore |
   |---|---|
   | `DATABASE_URL` | la connection string pooled di Neon |
   | `ENVIRONMENT` | `production` |
   | `ALLOWED_EMAILS` | gli indirizzi abilitati, separati da virgola |
   | `APP_BASE_URL` | `https://<tuo-dominio>.vercel.app` |
   | `BREVO_API_KEY` | la chiave API di Brevo |
   | `MAIL_FROM` | l'indirizzo mittente verificato su Brevo |
   | `MAIL_FROM_NAME` | `Wallet` |

   Per Brevo: registrati su [brevo.com](https://www.brevo.com) (piano gratuito, 300 email al
   giorno), in **Senders** aggiungi e verifica l'indirizzo che userai come `MAIL_FROM` —
   basta una singola email, **non serve un dominio** — poi in **SMTP & API → API Keys** crea
   la chiave.

   Due trappole che costano un pomeriggio:

   - **Serve la chiave API v3**, quella con prefisso `xkeysib-`. La chiave SMTP
     (`xsmtpsib-`) serve al relay di posta e viene rifiutata da questo endpoint.
   - **`MAIL_FROM` deve essere un indirizzo verificato.** L'API di Brevo accetta senza
     protestare anche un mittente non verificato, ma il messaggio fallisce i controlli
     SPF/DKIM e finisce nello spam: un `noreply@` inventato su un dominio che non possiedi
     *sembra* funzionare e in pratica non arriva.

4. **Deploy.** Al termine apri `https://<dominio>/_stato`: la stessa schermata di stato deve
   mostrare tutto verde. Controlla anche `https://<dominio>/api/health` direttamente.

5. **Le migrazioni non girano al deploy.** Su Vercel ogni richiesta è una funzione effimera e
   non è il posto dove modificare uno schema: prima di pubblicare codice che si aspetta
   tabelle nuove, lancia `alembic upgrade head` dalla tua macchina — punta allo stesso
   database Neon.

Se hai aggiunto le variabili dopo il primo deploy, rifai il deploy: Vercel non le inietta
retroattivamente.

### Le versioni in requirements.txt non sono decorative

Vercel compila su una versione recente di CPython e nell'immagine di build non c'è un
compilatore: ogni pacchetto con estensioni native deve avere un wheel già pronto per quella
versione di Python su manylinux, altrimenti il deploy si ferma con `No solution found when
resolving dependencies`.

In pratica riguarda `psycopg-binary`, `pydantic-core` (arriva con `pydantic`) e
`sqlalchemy`. Prima di abbassare un pin, controlla la sezione *Download files* su PyPI e
verifica che il wheel per quella versione ci sia. Quando Vercel passerà a un Python ancora
più recente, lo stesso errore si ripresenterà: **la soluzione è alzare i pin, non
abbassarli.**

## Come sta insieme

```
api/index.py       entrypoint Vercel: espone l'app FastAPI come serverless function
backend/app/       il backend vero e proprio
frontend/          React + Vite, build statica servita da Vercel
vercel.json        build del frontend + rewrite /api/* verso la function Python
requirements.txt   dipendenze Python di runtime, le legge Vercel dalla radice
```

Le rotte FastAPI includono il prefisso `/api` **nel percorso stesso**, non tramite
`root_path`: il rewrite di Vercel consegna alla function il percorso originale, quindi l'app
deve rispondere su `/api/health` sia in locale sia in produzione.
