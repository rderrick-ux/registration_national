# Registration National
 
A community-led platform that connects rural households in Rwanda to national birth registration.
Prototype for the Project Proposal and SRS by Rugwiro Derrick (African Leadership University, Introduction to Software Engineering).
 
- **Live app (public, no install needed):** https://registration-national.onrender.com/
- **Repository:** https://github.com/rderrick-ux/registration_national
Registration National is a **web app**. It runs in any modern browser on a computer or phone, so there is no APK or installer to download. To use it on a phone, open the live link in Chrome and choose **⋮ > Add to Home screen** to get an app icon.
 
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
 
These accounts are created automatically whenever the database is empty, both on the live app and on your computer.
 
> **Live app note:** it runs on Render's free tier. The first load after a quiet period can take up to a minute while the server wakes up. When the server restarts, records and new accounts are deleted, and only the demo accounts are recreated.
 
---
 
## Run it on your own computer
 
You need about 10 minutes. No packages or build step are required: the app uses only Python's standard library.
 
### Step 1: Install Python
 
1. Go to https://www.python.org/downloads/ and download Python 3.8 or newer.
2. Run the installer.
   - **Windows:** on the first screen, tick **Add python.exe to PATH**, then click **Install Now**.
   - **macOS:** run the `.pkg` file and click through.
   - **Linux:** Python 3 is usually already installed.
3. Open a terminal:
   - **Windows:** press the Windows key, type `PowerShell`, press Enter.
   - **macOS:** press `Cmd + Space`, type `Terminal`, press Enter.
4. Check that Python works:
```bash
python --version
```
   On Windows, if that fails, try `py --version`. You should see `Python 3.x.x`. If neither works, reinstall Python and make sure the PATH box is ticked.
 
### Step 2: Install Git
 
1. Go to https://git-scm.com/downloads, download Git for your system, and install it with the default options.
2. Close and reopen your terminal, then check:
```bash
git --version
```
 
You can skip Git: on the GitHub page, click **Code > Download ZIP**, unzip it, and go to Step 4.
 
### Step 3: Download the project
 
```bash
git clone https://github.com/rderrick-ux/registration_national.git
```
 
### Step 4: Go into the project folder
 
```bash
cd registration_national
```
 
If you downloaded the ZIP, the folder is called `registration_national-main`, so use `cd registration_national-main`. Every command after this runs from inside this folder (the one that contains `app.py`).
 
### Step 5: Start the server
 
```bash
python app.py
```
 
On Windows, if `python` doesn't work, use `py app.py`.
 
You should see:
```
Registration National is running
  Local:   http://127.0.0.1:8000
```
Keep this terminal window open while you use the app.
 
### Step 6: Open the app
 
Open http://127.0.0.1:8000 in Chrome, Edge or Firefox, and sign in with one of the [demo accounts](#demo-accounts).
 
All browser tabs and devices that open this address share one database, saved as `registration_national.db` in the project folder.
 
### Step 7: Stop the server
 
Click the terminal window and press `Ctrl + C`.
 
### Optional: open it on your phone
 
1. Connect your phone to the same Wi-Fi network as your computer.
2. Start the server with:
```bash
python app.py --host 0.0.0.0
```
3. On your phone, open the **Network** address the server prints, for example `http://192.168.1.20:8000`.
### Troubleshooting
 
| Problem | Fix |
|---|---|
| `python` is not recognised | Use `py` on Windows, or reinstall Python with **Add to PATH** ticked |
| `Address already in use` | Another program uses port 8000. Run `python app.py --port 9000` and open http://127.0.0.1:9000 |
| Phone can't connect | Check both devices are on the same Wi-Fi, and allow Python through your computer's firewall when asked |
| Wrong login or PIN | Check the [demo accounts](#demo-accounts). If you changed them, delete `registration_national.db` and restart the server to get them back |
| Want a fresh start | Stop the server, delete `registration_national.db`, and start it again |
 
### Without Python
 
Double-click `index.html` to open it in your browser. Data is then stored only in that browser, so the CHW and the registrar must use the same browser to see each other's records.
 
---
 
## Try the full flow (about 5 minutes)
 
1. Sign in as the **CHW**. Click **Online** in the top bar so it switches to **Offline**.
2. Click **Register a newborn**. Enter a National ID with fewer than 16 digits to see the error. Then complete the form and submit it; the record shows **Queued**.
3. Switch back to **Online**. Within a few seconds the record shows **Synced**.
4. Log out and sign in as the **Registrar**. Open **Review records**, click **Open**, and then click **Approve**. A tracking code (`RN-<year>-<6 digits>`) is created and the SMS is logged. To test corrections, use **Return to CHW** with a comment.
5. Sign in as the **CHW** again. The record shows **Approved** with its tracking code. A returned record shows the comment and can be edited and resubmitted.
6. Sign in as **admin** and look at **Dashboard**, **Users**, **Coverage** and **SMS log**.
A registrar sees only records from their own District + Sector. When you create new accounts, give the CHW and the registrar the same district and sector.
 
## Deploy your own copy
 
The live app is hosted on [Render](https://render.com). To deploy your own:
 
1. Fork this repository on GitHub (click **Fork** at the top right).
2. Sign in to https://render.com with your GitHub account.
3. Click **New > Web Service** and choose your fork.
4. Fill in the settings:
   - **Language / Runtime:** Python 3
   - **Build command:** leave empty (if Render requires one, enter `echo no build`)
   - **Start command:** `python app.py --host 0.0.0.0`
   - **Instance type:** Free
5. Click **Create Web Service**. After a few minutes Render shows your public URL, such as `https://<your-service>.onrender.com`.
The app reads the `PORT` variable that Render sets, so no other configuration is needed.
 
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
