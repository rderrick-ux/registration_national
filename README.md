# Registration National

A community-led platform that connects rural households in Rwanda to national birth registration.
Prototype for the Project Proposal and SRS by Rugwiro Derrick (African Leadership University, Introduction to Software Engineering).

- **Live app:** https://registration-national.onrender.com/
- **Repository:** https://github.com/rderrick-ux/registration_national

## What it does

Community Health Workers (CHWs) record newborns during home visits, even offline. Records are encrypted on the device and sync when a connection returns. The Sector Registrar approves them, and the parent then gets a tracking code by SMS.

| Role | Features |
|---|---|
| CHW (mobile view) | PIN login (works offline), 6-step birth form, 16-digit National ID check, drafts, encrypted local storage, auto-sync, fixing returned records |
| Sector Registrar | Dashboard, filter records by cell, status and date, **approve** (tracking code + SMS) or return with a comment, coverage by cell |
| Administrator | Dashboard, create and edit accounts (District / Sector / Cell / Village), national coverage, SMS log |

Every screen is available in English and Kinyarwanda (switch in the top bar).

## Demo accounts

| Role | Login | PIN | Jurisdiction |
|---|---|---|---|
| Administrator | `admin` | `1234` | National |
| Sector Registrar | `0788123987` | `2222` | Nyarugenge > Nyamirambo |
| CHW | `0798123456` | `1111` | Nyarugenge > Nyamirambo > Mumena |

These accounts are created automatically whenever the database is empty.

> **Note:** The live app runs on Render's free tier. When the service restarts, records and new accounts are deleted, and only the demo accounts are recreated. The first page load after a period of inactivity can take up to a minute.

## Run it locally

**Requirements:** Python 3.8+ (`python --version`; on Windows use `py --version`), Git and a modern browser. No packages and no build step.

```bash
git clone https://github.com/rderrick-ux/registration_national.git
cd registration_national
python app.py          # Windows: py app.py
```

Open http://127.0.0.1:8000. All browsers that open this address share one database (`registration_national.db`). To stop the server, press `Ctrl+C`.

- **Different port:** `python app.py --port 9000`
- **Test on a phone:** connect the phone to the same Wi-Fi, run `python app.py --host 0.0.0.0`, and open the **Network** address the server prints.
- **Without Python:** open `index.html` directly. Data is then stored only in that browser, so the CHW and the registrar must use the same browser.

## Try the full flow (about 5 minutes)

1. Sign in as the **CHW**. Click **Online** in the top bar so it switches to **Offline**.
2. Click **Register a newborn**. Enter a National ID with fewer than 16 digits to see the error. Then complete the form and submit it; the record shows **Queued**.
3. Switch back to **Online**. Within a few seconds the record shows **Synced**.
4. Log out and sign in as the **Registrar**. Open **Review records**, click **Open**, and then click **Approve**. A tracking code (`RN-<year>-<6 digits>`) is created and the SMS is logged. To test corrections, use **Return to CHW** with a comment.
5. Sign in as the **CHW** again. The record shows **Approved** with its tracking code. A returned record shows the comment and can be edited and resubmitted.
6. Sign in as **admin** and look at **Dashboard**, **Users**, **Coverage** and **SMS log**.

A registrar sees only records from their own District + Sector. When you create accounts, give the CHW and the registrar the same district and sector.

## Deployment

The app is hosted on [Render](https://render.com) as a Python web service:

- **Build command:** none
- **Start command:** `python app.py --host 0.0.0.0` (the app reads `PORT` automatically)

## Project structure

```
index.html        entry point
app.py            Python server: serves the app and a JSON sync API stored in SQLite
css/styles.css    styles
img/              logo and icon
js/geo.js         Rwanda's 5 provinces, 30 districts, 416 sectors and 2,148 cells
js/core.js        helpers, translations, AES-256 encryption, storage, demo accounts
js/chw.js         CHW app: form wizard, validation, encrypted store, sync
js/portal.js      registrar portal, admin console, coverage
js/app.js         app shell, login, rendering
```

## SRS traceability

| Requirement | Where |
|---|---|
| FR 1.1 Phone + PIN login, offline credential cache | `js/app.js` `doLogin`, `js/core.js` `refreshCache` |
| FR 1.2 Assign District / Sector / Cell / Village | `js/portal.js` `admHTML`, `updUser`; `js/geo.js` |
| FR 2.1 Offline birth record | `js/chw.js` wizard |
| FR 2.2 16-digit National ID | `js/chw.js` `validate` |
| FR 2.3 / NFR 1 AES-256 local storage | `js/core.js` `seal` / `unseal` (AES-256-GCM, key from PIN via PBKDF2) |
| FR 3.1 / 3.2 Auto-sync and status labels | `js/chw.js` `sync` (every 4 s and on reconnect) |
| FR 4.1 / 4.2 Review; approve or return | `js/portal.js` `regHTML`, `decide` |
| FR 5.1 SMS tracking code | `js/portal.js` `decide` (SMS log) |
| FR 5.2 Coverage by cell | `js/portal.js` `covHTML` |

## Prototype limits

- The backend uses Python + SQLite instead of Node.js/PostgreSQL. Local encryption uses Web Crypto instead of SQLCipher.
- SMS messages are written to a log; they are not sent through MTN or Airtel. NIDA checks, OAuth2 and TLS are not simulated. The top-bar toggle only simulates losing the connection.
- The sync API has no authentication, and each save replaces the whole database. If two users save at the same moment, one change can be lost.
- Location data comes from the MIT-licensed `rwanda` npm package (v3.0.4), corrected against the NISR list. Villages are typed in as free text.
- Some sector names repeat across districts, so accounts and records are always scoped by District + Sector.

## Contributing

Create a feature branch (`git checkout -b feature/<name>`), commit your changes, push, and open a pull request into `main`.
