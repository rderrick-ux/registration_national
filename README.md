# Registration National

A community-led platform that connects rural households in Rwanda to national civil (birth) registration.
Prototype of the Project Proposal and SRS by Rugwiro Derrick (African Leadership University, Introduction to Software Engineering).

**Live demo:** `https://<your-github-username>.github.io/<repo-name>/` (see [Deploy](#7-deploy-to-a-public-url))

## What it does

Community Health Workers (CHWs) record newborns offline during home visits. Records are encrypted on the device, sync when a connection returns, and are approved by the Sector Civil Registrar. The parent then gets a tracking code by SMS.

| Role | What they can do |
|---|---|
| CHW (mobile view) | PIN login (works offline), 6-step birth form, 16-digit National ID check, drafts, encrypted local storage, auto-sync, fix returned records |
| Sector Registrar | Dashboard, review records by cell, status and date, **approve** (tracking code + SMS) or return with a comment, coverage by cell |
| Administrator | Dashboard, create and edit accounts (District / Sector / Cell / Village), national coverage, SMS log |

Every screen is available in English and Kinyarwanda (switch in the top bar). Have a native speaker review the Kinyarwanda before real use.

## 1. Requirements

- A modern browser: Chrome, Edge or Firefox.
- Python 3.8 or newer for the shared-database server (recommended). Check with `python --version` (Windows: `py --version`). Install from [python.org](https://www.python.org/downloads/) if missing; on Windows tick **Add Python to PATH** during install.
- Git (only if you clone instead of downloading the zip).

No packages, no build step.

## 2. Get the code

Either unzip the project folder, or clone it:

```bash
git clone https://github.com/<your-github-username>/<repo-name>.git
cd <repo-name>
```

All commands below are run from inside this folder (the one that contains `app.py`).

## 3. Run it

### Option A: Python server (recommended, shared database)

```bash
python app.py        # Windows: py app.py
```

Open `http://127.0.0.1:8000`. Every browser and device that opens this address shares the same records, stored in `registration_national.db` next to `app.py`. Stop the server with `Ctrl+C`.

- **Other port:** `python app.py --port 9000` (or set the `PORT` environment variable). Use this if you see "Address already in use".
- **Test on a phone:** connect the phone to the same Wi-Fi, run `python app.py --host 0.0.0.0`, and open the **Network** address it prints (for example `http://192.168.1.20:8000`). If the phone cannot connect, allow Python through the computer's firewall.

### Option B: Browser only (no shared database)

Double-click `index.html`, or run `python -m http.server 8000` and open `http://localhost:8000`. Data is kept in that browser's `localStorage`, so the CHW and the registrar must use **the same browser** to see each other's records.

## 4. First login and accounts

On first start the app creates one administrator:

| Login | PIN |
|---|---|
| `admin` | `1234` |

1. Sign in as `admin` / `1234` and open **Users**.
2. Create each account: full name, role, login (phone number or username), a 4-digit PIN, then District > Sector (> Cell and Village for CHWs). The lists cascade.
3. A registrar only sees records from their own **District + Sector**, so give the CHW and the registrar the same district and sector.
4. Create your own administrator account, sign in with it, and remove the default `admin`.

A CHW can sign in offline only on a device where the account was already loaded while online.

## 5. Try the full flow (about 5 minutes)

1. As `admin`, create a CHW (login `0788000001`, PIN `1234`, Rubavu > Gisenyi > Umuganda, village Kabuga) and a registrar (login `registrar`, PIN `4321`, Rubavu > Gisenyi). Log out.
2. Sign in as the CHW. Click **Online** in the top bar so it shows **Offline**.
3. Choose **Register a newborn**. Enter a National ID with fewer than 16 digits to see the error, then complete the child, mother, father and witness steps and submit. The record shows **Queued**.
4. Click **Offline** to go back online. Within a few seconds the record shows **Synced** (or click **Sync now**).
5. Log out and sign in as `registrar`. Approve the record (see section 6). To test corrections, return another record with a comment.
6. Sign in as the CHW. The record shows **Approved** with its tracking code. A returned record shows the comment; edit it and resubmit.
7. Sign in as `admin` and check **Dashboard**, **SMS log** and **Coverage**. Switch the language to Kinyarwanda.

## 6. Approving records

Approval happens in the **Sector Registrar** portal; the administrator portal only views totals, coverage and the SMS log.

1. The CHW's record must be **Synced** (CHW online and synced).
2. Sign in as a registrar for the record's District + Sector. The portal needs the top bar to show **Online**.
3. Open **Review records**. Optionally filter by cell, status (**Synced** = awaiting review) or date.
4. Click **Open** on the record, check the details, and click **Approve**. A comment is not needed to approve.

Result: the status becomes **Approved**, a tracking code (`RN-<year>-<6 digits>`) is created, an SMS to the mother's phone is written to the SMS log, and the CHW's app shows Approved on its next sync. **Return to CHW** (comment required) sends it back instead; once the CHW fixes and resubmits it, it returns as Synced and can be approved.

## 7. Deploy to a public URL

Without `app.py` the app runs in browser-only mode (Option B).

**GitHub Pages**
1. Push the project to a public GitHub repository (`index.html` at the root).
2. Go to **Settings > Pages**. Under **Source** choose **Deploy from a branch**, select `main` and `/ (root)`, and click **Save**.
3. After a minute the site is at `https://<your-github-username>.github.io/<repo-name>/`. Paste it at the top of this README.

**Netlify or Vercel:** drag the folder onto Netlify Drop, or import the repository in Vercel. No build command; publish directory is the root.

**Shared database online:** host `app.py` on any service that runs Python (for example Render or Railway) with start command `python app.py --host 0.0.0.0` (it reads `PORT` automatically).

## 8. Reset all data

- **Python server:** stop it, delete `registration_national.db`, start it again.
- **Browser:** open DevTools (`F12`) > **Application** > **Storage** > **Clear site data**, then reload. This also clears CHW drafts and offline queues on that device.

Both together give a completely fresh start with only `admin` / `1234`.

## Project structure

```
index.html        entry point
app.py            Python server: serves the app (its own embedded copy) + REST sync API on SQLite
css/styles.css    styles
js/geo.js         all 5 provinces, 30 districts, 416 sectors and 2,148 cells of Rwanda, plus lookups
js/core.js        helpers, translations, AES-256 encryption, storage, first-run admin
js/chw.js         CHW app: form wizard, validation, encrypted store, sync
js/portal.js      registrar portal, admin console, coverage
js/app.js         app shell, login, rendering
```

`app.py` contains an exact copy of `index.html`, the CSS and the JS. If you edit a file in `css/` or `js/`, make the same change inside `app.py`, otherwise the Python server keeps serving the old version.

## SRS traceability

| SRS requirement | Where |
|---|---|
| FR 1.1 Phone + PIN login, offline credential cache | `js/app.js` `doLogin`, `js/core.js` `refreshCache` |
| FR 1.2 Assign District / Sector / Cell / Village | `js/portal.js` `admHTML`, `updUser`; `js/geo.js` |
| FR 2.1 Offline birth record (child, parents, witnesses) | `js/chw.js` wizard |
| FR 2.2 16-digit National ID | `js/chw.js` `validate` |
| FR 2.3 / NFR 1 AES-256 local storage | `js/core.js` `seal`/`unseal` (AES-256-GCM, PBKDF2 key from PIN) |
| FR 3.1 / 3.2 Auto-sync and status markers | `js/chw.js` `sync` (every 4 s and on reconnect) |
| FR 4.1 / 4.2 Review by sector, cell, date; approve or return | `js/portal.js` `regHTML`, `decide` |
| FR 5.1 SMS tracking code | `js/portal.js` `decide` (SMS log) |
| FR 5.2 Coverage by cell | `js/portal.js` `covHTML` |
| Jurisdiction check on sync | `js/chw.js` `sync` rejects records outside the CHW's District + Sector |

## Prototype limits

- Backend is Python + SQLite (`app.py`), not Node.js/PostgreSQL. Local encryption uses Web Crypto, not SQLCipher.
- SMS is written to a log, not sent through MTN or Airtel. NIDA, OAuth2 and TLS are not simulated; the top-bar toggle simulates connectivity.
- Location data comes from the MIT-licensed `rwanda` npm package (v3.0.4), corrected against the NISR list. Villages are free text. Check against current NISR/NIDA lists before real use.
- 30 sector names repeat across districts (Remera is in four), so accounts and records are always scoped by District + Sector.

## Contributing

Create a feature branch (`git checkout -b feature/<name>`), commit, push, and open a pull request into `main`.

## References

Ministry of Health Rwanda (2018), National Identification Authority, NISR (2026), UNICEF CRVS repository and WHO (2021) CRVS Strategic Implementation Plan, as cited in the project SRS.
