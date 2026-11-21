#!/usr/bin/env python3
"""
Registration National - single-file prototype (Python 3.8+, standard library only).

Run:      python app.py
Open:     http://127.0.0.1:8000
Phones:   python app.py --host 0.0.0.0   then open http://<this-computer-ip>:8000

What it does
  * Serves the web app (CHW mobile view, registrar portal, admin console).
  * Provides the Sync API (REST/JSON) and stores all data in SQLite
    (registration_national.db next to this file), so every browser and device
    that opens the app shares the same records.
  * CHW devices still keep their own AES-256 encrypted offline queue in the browser.

API
  GET  /api/ping   health check
  GET  /api/db     read the shared database (404 until first seeded)
  POST /api/db     replace the shared database (JSON body)
  POST /api/reset  delete all shared data and re-seed on next page load
"""
import argparse
import json
import os
import socket
import sqlite3
import threading
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registration_national.db")
MAX_BODY = 20 * 1024 * 1024
LOCK = threading.Lock()

# ---------------------------------------------------------------------------
# Web app (HTML + CSS + JavaScript)
# ---------------------------------------------------------------------------
PAGE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Registration National</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🍼</text></svg>">
<style>
:root {
  --bg: #edf4f1;
  --card: #fff;
  --fg: #10242b;
  --mut: #587078;
  --pri: #0d5c4b;
  --pri-d: #094536;
  --on: #fff;
  --acc: #f4b81c;
  --bd: #dce7e3;
  --bad: #b3261e;
  --ok: #17803d;
  --warn: #9a6a00;
  --sh: 0 1px 2px #10242b12,0 8px 22px #10242b0f;
}
@media(prefers-color-scheme:dark) {
  :root {
    --bg: #0b1517;
    --card: #13242a;
    --fg: #e8f1ef;
    --mut: #92a9ac;
    --pri: #2fa98d;
    --pri-d: #4cc2a6;
    --on: #06241d;
    --bd: #233a40;
    --bad: #ff8f86;
    --ok: #63d78f;
    --warn: #f4b81c;
    --sh: none;
  }
}
* {
  box-sizing: border-box;
}
html {
  scroll-behavior: smooth;
}
body {
  margin: 0;
  font: 16px/1.5 "Segoe UI",system-ui,-apple-system,Roboto,sans-serif;
  background: var(--bg);
  color: var(--fg);
}
h1,h2,h3,h4 {
  margin: 0;
  line-height: 1.2;
  letter-spacing: -.01em;
}
h2 {
  font-size: 22px;
}
h3 {
  font-size: 19px;
}
h4 {
  font-size: 15px;
}
#bar {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px 16px;
  background: linear-gradient(135deg,#0b4d3e,#0e6a56);
  color: #fff;
  position: sticky;
  top: 0;
  z-index: 5;
  flex-wrap: wrap;
  border-bottom: 3px solid var(--acc);
}
.brand {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 17px;
  font-weight: 700;
}
.logo {
  display: inline-grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  background: var(--acc);
  color: #0b4d3e;
}
.logo.big {
  width: 52px;
  height: 52px;
  border-radius: 15px;
  margin-bottom: 16px;
}
.sp {
  flex: 1;
}
#bar select,#bar .pill {
  background: #ffffff1f;
  color: #fff;
  border: 1px solid #ffffff55;
  border-radius: 999px;
  padding: 6px 12px;
  min-height: 36px;
  width: auto;
  font-size: 14px;
}
#bar select option {
  color: #000;
}
.pill:before {
  content: "";
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  margin-right: 7px;
  background: #6ff0a0;
}
.pill.off:before {
  background: var(--acc);
}
main {
  max-width: 1000px;
  margin: 0 auto;
  padding: 16px 14px 40px;
}
.phone {
  max-width: 480px;
  margin-left: auto;
  margin-right: auto;
}
.card {
  background: var(--card);
  border: 1px solid var(--bd);
  border-radius: 14px;
  padding: 18px;
  margin: 12px 0;
  box-shadow: var(--sh);
}
.card>button {
  margin-top: 14px;
}
label {
  display: block;
  margin: 14px 0 5px;
  font-size: 14px;
  font-weight: 600;
}
input,select,textarea {
  width: 100%;
  min-height: 48px;
  padding: 11px 13px;
  border: 2px solid var(--bd);
  border-radius: 11px;
  background: var(--bg);
  color: var(--fg);
  font: inherit;
}
input:focus,select:focus,textarea:focus,button:focus-visible {
  outline: none;
  border-color: var(--pri);
  box-shadow: 0 0 0 4px #f4b81c66;
}
button {
  min-height: 48px;
  background: var(--pri);
  color: var(--on);
  border: 0;
  border-radius: 11px;
  padding: 10px 18px;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: transform .08s,background .15s;
}
button:hover {
  background: var(--pri-d);
}
button:active {
  transform: scale(.98);
}
button.ghost {
  background: transparent;
  color: var(--pri);
  border: 2px solid var(--pri);
}
button.ghost:hover {
  background: #0d5c4b14;
}
button.ghost.light {
  color: #fff;
  border-color: #ffffff88;
  min-height: 36px;
  padding: 4px 14px;
  border-radius: 999px;
}
button.text {
  background: none;
  color: var(--mut);
  min-height: 36px;
  padding: 4px 8px;
}
button.bad {
  background: var(--bad);
  color: #fff;
}
button.cta {
  width: 100%;
  font-size: 17px;
  min-height: 56px;
  background: var(--acc);
  color: #0b2a22;
  box-shadow: var(--sh);
}
button.cta:hover {
  background: #ffc93a;
}
.row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}
.between {
  justify-content: space-between;
}
.muted {
  color: var(--mut);
  font-size: 14px;
}
.err {
  color: var(--bad);
  font-size: 14px;
  margin-top: 5px;
  font-weight: 600;
}
.hint {
  color: var(--mut);
  font-size: 13px;
  margin-top: 4px;
}
.chip {
  display: inline-block;
  padding: 3px 11px;
  border-radius: 999px;
  background: #0d5c4b18;
  color: var(--pri);
  font-size: 13px;
  font-weight: 600;
}
.chip.big {
  background: #d3f2dd;
  color: #0e5a29;
  font-size: 15px;
  margin-top: 8px;
}
.greet {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 10px;
  flex-wrap: wrap;
  margin: 6px 0 4px;
}
.banner {
  background: #fff3cf;
  color: #5b4300;
  border: 1px solid #f1d27a;
  border-radius: 11px;
  padding: 11px 14px;
  margin: 10px 0;
  font-size: 14px;
}
.hero {
  background: radial-gradient(circle at 88% 12%,#f4b81c40,transparent 42%),linear-gradient(135deg,#0b4d3e,#10806a);
  color: #fff;
  border-radius: 20px;
  padding: 30px 24px;
  margin: 6px auto 8px;
  max-width: 480px;
}
.hero h1 {
  font-size: clamp(26px,6vw,34px);
  max-width: 14em;
}
.hero p {
  margin: 12px 0 0;
  opacity: .92;
  max-width: 30em;
}
.demos {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 12px;
}
button.demo {
  background: var(--bg);
  color: var(--fg);
  border: 2px solid var(--bd);
  text-align: left;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 10px 12px;
}
button.demo:hover {
  border-color: var(--pri);
  background: var(--bg);
}
button.demo span {
  font-weight: 400;
  font-size: 13px;
  color: var(--mut);
}
.tabs {
  display: inline-flex;
  gap: 4px;
  background: var(--card);
  border: 1px solid var(--bd);
  border-radius: 999px;
  padding: 4px;
  margin: 12px 0 4px;
  flex-wrap: wrap;
}
.tabs button {
  min-height: 38px;
  background: transparent;
  color: var(--fg);
  padding: 6px 16px;
  border-radius: 999px;
}
.tabs button.on {
  background: var(--pri);
  color: var(--on);
}
.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit,minmax(96px,1fr));
  gap: 10px;
  margin: 12px 0;
}
.tile {
  background: var(--card);
  border: 1px solid var(--bd);
  border-radius: 13px;
  padding: 12px 14px;
  box-shadow: var(--sh);
}
.tile b {
  display: block;
  font-size: 28px;
  line-height: 1.1;
}
.tile span {
  font-size: 13px;
  color: var(--mut);
}
.tile.warn b {
  color: var(--warn);
}
.tile.ok b {
  color: var(--ok);
}
.tile.bad b {
  color: var(--bad);
}
.rec {
  background: var(--card);
  border: 1px solid var(--bd);
  border-left: 6px solid var(--bd);
  border-radius: 13px;
  padding: 14px 16px;
  margin: 10px 0;
  box-shadow: var(--sh);
}
.rec[data-s=Queued] {
  border-left-color: var(--acc);
}
.rec[data-s=Synced] {
  border-left-color: #2f7fd0;
}
.rec[data-s=Approved] {
  border-left-color: var(--ok);
}
.rec[data-s=Flagged] {
  border-left-color: var(--bad);
}
.empty {
  text-align: center;
  padding: 30px 10px;
  color: var(--mut);
}
.badge {
  padding: 3px 11px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}
.Draft {
  background: #e3e7ea;
  color: #33414a;
}
.Queued {
  background: #fff0c2;
  color: #6b4e00;
}
.Synced {
  background: #d6e9ff;
  color: #0b3d73;
}
.Approved {
  background: #d3f2dd;
  color: #0e5a29;
}
.Flagged {
  background: #ffd9d6;
  color: #8a1c14;
}
.steps {
  display: flex;
  gap: 5px;
  margin: 10px 0 14px;
}
.steps i {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: var(--bd);
}
.steps i.done {
  background: var(--pri);
}
.steps i.cur {
  background: var(--acc);
}
.seg {
  display: flex;
  gap: 8px;
}
.seg button {
  flex: 1;
  background: var(--bg);
  color: var(--fg);
  border: 2px solid var(--bd);
}
.seg button.on {
  background: var(--pri);
  color: var(--on);
  border-color: var(--pri);
}
.actions {
  position: sticky;
  bottom: 0;
  display: flex;
  gap: 8px;
  padding: 14px 0 10px;
  background: linear-gradient(transparent,var(--bg) 28%);
}
.actions button {
  flex: 1;
  margin: 0;
}
.actions button.go {
  flex: 2;
}
.sec {
  padding: 10px 0;
  border-bottom: 1px solid var(--bd);
}
.sec:last-of-type {
  border: 0;
}
dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 3px 14px;
  margin: 6px 0 0;
}
dt {
  color: var(--mut);
  font-size: 14px;
}
dd {
  margin: 0;
  font-weight: 600;
  word-break: break-word;
}
.meter {
  height: 7px;
  background: var(--bd);
  border-radius: 4px;
  width: 96px;
  margin-bottom: 3px;
}
.meter i {
  display: block;
  height: 100%;
  background: var(--ok);
  border-radius: 4px;
}
.scroll {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th,td {
  padding: 11px 10px;
  border-bottom: 1px solid var(--bd);
  text-align: left;
  vertical-align: top;
}
th {
  font-size: 13px;
  color: var(--mut);
  font-weight: 600;
}
tr:hover td {
  background: #0d5c4b0b;
}
td button {
  min-height: 36px;
  padding: 4px 12px;
  margin: 0;
}
td input,td select {
  min-height: 38px;
  padding: 6px 8px;
}
.filters {
  display: grid;
  grid-template-columns: repeat(auto-fit,minmax(150px,1fr));
  gap: 12px;
}
.thumb {
  max-width: 100%;
  max-height: 200px;
  margin-top: 10px;
  border-radius: 10px;
}
.modal {
  position: fixed;
  inset: 0;
  background: #06141199;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 14px;
  z-index: 20;
}
.modal .card {
  max-width: 540px;
  width: 100%;
  max-height: 92vh;
  overflow: auto;
  margin: 0;
}
#toast {
  position: fixed;
  left: 50%;
  bottom: 24px;
  transform: translate(-50%,30px);
  background: #10242b;
  color: #fff;
  padding: 12px 18px;
  border-radius: 12px;
  opacity: 0;
  transition: .25s;
  z-index: 30;
  max-width: 90%;
  box-shadow: 0 8px 24px #0006;
  border-left: 5px solid var(--acc);
}
#toast.show {
  opacity: 1;
  transform: translate(-50%,0);
}
footer {
  text-align: center;
  color: var(--mut);
  font-size: 13px;
  padding: 10px 20px 30px;
}
@media(prefers-reduced-motion:reduce) {
  * {
    transition: none!important;
  }
}
</style>
</head>
<body>
<header id="bar"></header>
<main id="app"></main>
<footer>Registration National prototype. Demo data only; no real NIDA or SMS integration.</footer>
<div id="toast" role="status" aria-live="polite"></div>
<script>
/* ===== core.js: Helpers, translations, encryption, storage layer, seed data ===== */
/* Registration National - core: helpers, i18n, AES-256-GCM encryption, simulated server (PostgreSQL stand-in) */
const G = id => document.getElementById(id);
const LS = localStorage;
const J = (k, d) => { try {
  const v = JSON.parse(LS.getItem(k));
  return v ?? d;
} catch { return d; } };
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const uid = () => crypto.randomUUID();
const rnd = n => Array.from({ length: n }, () => Math.floor(Math.random() * 10)).join('');
const nidOK = v => /^\d{16}$/.test(v || '');
const phOK = v => /^07[2389]\d{7}$/.test(v || '');
/* Storage: use the Python server (shared SQLite database) when it is available, otherwise this browser's localStorage */
function xhr(method, url, body) {
  const x = new XMLHttpRequest();
  x.open(method, url, false);
  if (body) x.setRequestHeader('Content-Type', 'application/json');
  x.send(body || null);
  return x;
}
const apiOK = (() => {
  try { return xhr('GET', '/api/ping').status === 200; } catch { return false; }
})();
const S = (k, v) => {
  if (k === 'rn_server' && apiOK) xhr('POST', '/api/db', JSON.stringify(v));
  else LS.setItem(k, JSON.stringify(v));
};
const DB = () => {
  if (!apiOK) return J('rn_server', null);
  const x = xhr('GET', '/api/db');
  return x.status === 200 ? JSON.parse(x.responseText) : null;
};
const net = () => LS.getItem('rn_net') !== 'off';

/* Sample jurisdictions (Rubavu District, Western Province) */
const GEO = { Gisenyi: ['Umuganda', 'Rubavu', 'Nengo'], Nyamyumba: ['Burushya', 'Gikombe', 'Rubona'], Rugerero: ['Basa', 'Kageshi', 'Muhira'] };

/* i18n: Kinyarwanda + English (NFR 4 / 6.5) */
const L = {
  en: { app: 'Registration National', welcome: 'Welcome', hero1: 'Every birth counted, even offline.', hero2: 'Register newborns at home, sync later, and send parents a tracking code by SMS.', register: 'Register a newborn', cancel: 'Cancel', login: 'Sign in', user: 'Phone number or username', pin: 'PIN', logout: 'Log out', online: 'Online', offline: 'Offline', records: 'My records', newrec: 'New birth record', step: 'Step', child: 'Child', mother: 'Mother', father: 'Father (optional)', witness1: 'Witness 1', witness2: 'Witness 2 (optional)', given: 'Given name', family: 'Family name', dob: 'Date of birth', pob: 'Place of birth', gender: 'Gender', M: 'Male', F: 'Female', nid: 'National ID (16 digits)', phone: 'Phone (07XXXXXXXX)', address: 'Address', next: 'Next', back: 'Back', savedraft: 'Save draft', submit: 'Submit', review: 'Review and submit', photo: 'Photo of parent ID (optional)', none: 'No records yet', tracking: 'Tracking code', edit: 'Edit', del: 'Delete', syncnow: 'Sync now', waiting: 'Waiting to sync', req: 'Required', nid16: 'ID must be 16 digits', phbad: 'Use format 07XXXXXXXX', dobfut: 'Date cannot be in the future', fix: 'Fix the highlighted fields', saved: 'Saved offline. It will sync when you are online.', sent: 'Submitted and synced', draftsaved: 'Draft saved', offnote: 'You are offline. Records stay queued.', synced: 'Synced records:', Draft: 'Draft', Queued: 'Queued', Synced: 'Synced', Approved: 'Approved', Flagged: 'Needs correction' },
  rw: { welcome: 'Murakaza neza', hero1: 'Buri mwana wese yandikwe, nubwo nta interineti.', hero2: 'Andika abana bavutse mu ngo, wohereze nyuma, ababyeyi bahabwe kode ikurikirana kuri SMS.', register: 'Andika umwana mushya', cancel: 'Reka', login: 'Injira', user: 'Telefone cyangwa izina', pin: "Umubare w'ibanga", logout: 'Sohoka', online: 'Hari interineti', offline: 'Nta interineti', records: 'Inyandiko zanjye', newrec: 'Andika umwana mushya', step: 'Intambwe', child: 'Umwana', mother: 'Mama', father: 'Papa (si ngombwa)', witness1: 'Umutangabuhamya 1', witness2: 'Umutangabuhamya 2 (si ngombwa)', given: 'Izina bwite', family: "Izina ry'umuryango", dob: "Itariki y'amavuko", pob: 'Aho yavukiye', gender: 'Igitsina', M: 'Gabo', F: 'Gore', nid: 'Indangamuntu (imibare 16)', phone: 'Telefone', address: 'Aho atuye', next: 'Komeza', back: 'Subira inyuma', savedraft: "Bika nk'inyandiko", submit: 'Ohereza', review: 'Kureba no kohereza', none: 'Nta nyandiko zihari', tracking: 'Kode ikurikirana', edit: 'Hindura', del: 'Siba', syncnow: 'Ohereza ubu', waiting: 'Zitegereje kohereza', req: 'Bikenewe', nid16: 'Indangamuntu igomba kuba imibare 16', Draft: 'Inyandiko', Queued: 'Mu murongo', Synced: 'Byoherejwe', Approved: 'Byemejwe', Flagged: 'Bikosorwe' }
};
let lang = LS.getItem('rn_lang') || 'en';
const t = k => (L[lang] && L[lang][k]) || L.en[k] || k;

/* AES-256-GCM via Web Crypto; key derived from PIN with PBKDF2 (stand-in for SQLCipher on the phone) */
const enc = new TextEncoder(), dec = new TextDecoder();
const b64 = b => { let s = '';
for (const x of new Uint8Array(b)) s += String.fromCharCode(x);
return btoa(s); };
const unb64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
const sha = async s => b64(await crypto.subtle.digest('SHA-256', enc.encode(s)));
async function deriveKey(pin, salt) {
  const m = await crypto.subtle.importKey('raw', enc.encode(pin), 'PBKDF2', false, ['deriveKey']);
  return crypto.subtle.deriveKey({ name: 'PBKDF2', salt: enc.encode(salt), iterations: 100000, hash: 'SHA-256' }, m, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']);
}
async function seal(key, obj) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  return b64(iv) + '.' + b64(await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, enc.encode(JSON.stringify(obj))));
}
async function unseal(key, s) {
  if (!s) return [];
  const [iv, ct] = s.split('.');
  return JSON.parse(dec.decode(await crypto.subtle.decrypt({ name: 'AES-GCM', iv: unb64(iv) }, key, unb64(ct))));
}

const logS = (db, m) => { db.log.unshift({ at: new Date().toISOString(), m });
db.log.length = Math.min(db.log.length, 100); };

/* Seed demo data on first load */
async function seed() {
  if (DB()) return;
  const mk = async (id, name, role, login, pin, sector, cell, village) => ({ id, name, role, login, hash: await sha(login + ':' + pin), sector, cell, village });
  const users = [
    await mk('u1', 'Aline Mukamana', 'chw', '0788000001', '1234', 'Gisenyi', 'Umuganda', 'Kabuga'),
    await mk('u2', 'Jean Bosco Habimana', 'chw', '0788000002', '2345', 'Nyamyumba', 'Burushya', 'Nyarubande'),
    await mk('u3', 'Grace Uwase', 'registrar', 'registrar', '4321', 'Gisenyi', '', ''),
    await mk('u5', 'Eric Ndayisaba', 'registrar', 'registrar2', '4322', 'Nyamyumba', '', ''),
    await mk('u4', 'System Admin', 'admin', 'admin', '9999', '', '', '')
  ];
  const names = ['Keza', 'Iradukunda', 'Mugisha', 'Uwimana', 'Ishimwe', 'Niyonsenga', 'Umutoni', 'Cyiza'];
  const demo = [['Umuganda', 'Gisenyi', 'u1', 'Approved'], ['Umuganda', 'Gisenyi', 'u1', 'Synced'], ['Rubavu', 'Gisenyi', 'u1', 'Synced'], ['Nengo', 'Gisenyi', 'u1', 'Flagged'], ['Rubavu', 'Gisenyi', 'u1', 'Approved'], ['Burushya', 'Nyamyumba', 'u2', 'Synced'], ['Gikombe', 'Nyamyumba', 'u2', 'Approved']];
  const records = demo.map(([cell, sector, chw, status], i) => ({
    id: uid(), status, createdAt: new Date(Date.now() - (i + 1) * 864e5).toISOString(), chw, sector, cell, village: 'Demo',
    child: { given: names[i], family: 'Demo', dob: new Date(Date.now() - (i + 3) * 864e5).toISOString().slice(0, 10), pob: cell, gender: i % 2 ? 'F' : 'M' },
    mother: { given: 'Mama ' + names[i], family: 'Demo', nid: '1' + rnd(15), phone: '0788' + rnd(6) }, father: {}, w1: { given: 'Witness', family: 'Demo', nid: '1' + rnd(15), address: cell }, w2: {}, photo: '',
    tracking: status === 'Approved' ? 'RN-2026-' + rnd(6) : '', flag: status === 'Flagged' ? 'Mother National ID does not match the record. Please re-check.' : ''
  }));
  const db = { users, records, sms: [], log: [] };
  logS(db, 'Demo data seeded');
  S('rn_server', db);
}

/* Refresh the offline credential cache whenever the device is online (FR 1.1) */
function refreshCache() {
  const db = DB();
  if (net() && db) S('rn_cred', db.users);
}

const tiles = l => `<div class="tiles">${l.map(x => `<div class="tile ${x[2] || ''}"><b>${x[0]}</b>
  <span>${x[1]}</span></div>`).join('')}</div>`;


/* ===== chw.js: CHW mobile client ===== */
/* CHW mobile client: offline intake wizard, encrypted local DB, auto-sync (FR 1-3) */
const STEPS = [
  { k: 'child', f: ['given', 'family', 'dob', 'pob', 'gender'], r: 1 },
  { k: 'mother', f: ['given', 'family', 'nid', 'phone'], r: 1 },
  { k: 'father', f: ['given', 'family', 'nid', 'phone'], r: 0 },
  { k: 'w1', f: ['given', 'family', 'nid', 'address'], r: 1 },
  { k: 'w2', f: ['given', 'family', 'nid', 'address'], r: 0 }
];
const TITLES = { child: 'child', mother: 'mother', father: 'father', w1: 'witness1', w2: 'witness2' };
let W = null, busy = false;
const lk = () => 'rn_local_' + ME.id;
const loadLocal = () => unseal(KEY, LS.getItem(lk()));
const saveLocal = async a => LS.setItem(lk(), await seal(KEY, a));

/* FR 2.2: validate 16-digit National ID (plus phone/date format) */
function validate(st, d = {}) {
  const e = {}, any = Object.values(d).some(x => x);
  st.f.forEach(f => {
    const v = (d[f] || '').trim();
    const req = st.r ? true : (any && f !== 'phone');
    if (req && !v) e[f] = t('req');
    else if (v) {
      if (f === 'nid' && !nidOK(v)) e[f] = t('nid16');
      if (f === 'phone' && !phOK(v)) e[f] = t('phbad');
      if (f === 'dob' && new Date(v) > new Date()) e[f] = t('dobfut');
    }
  });
  return e;
}
const fmtErr = d => STEPS.some(st => { const x = d[st.k] || {}; return (x.nid && !nidOK(x.nid)) || (x.phone && !phOK(x.phone)); });
function collect() {
  if (W.step >= 5) return;
  const st = STEPS[W.step], o = {};
  st.f.forEach(f => { const el = G('f_' + f); if (el) o[f] = el.value.trim(); });
  W.d[st.k] = o;
}

const HINTS = { pob: 'Village or health facility', phone: 'We send the tracking code to this number by SMS' };
function setG(g, btn) {
  G('f_gender').value = g;
  btn.parentNode.querySelectorAll('button').forEach(b => b.classList.toggle('on', b === btn));
}
function jump(i) {
  W.step = i;
  W.err = null;
  render();
}
const stepper = () => `<div class="steps">${[0, 1, 2, 3, 4, 5].map(i => `<i class="${i < W.step ? 'done' : i === W.step ? 'cur' : ''}">
  </i>`).join('')}</div>`;
function wizHTML() {
  const s = W.step;
  if (s === 5) return reviewHTML();
  const st = STEPS[s], d = W.d[st.k] || {}, e = W.err || {};
  const inputs = st.f.map(f => {
    let inp, hint = HINTS[f] ? `<div class="hint">${HINTS[f]}</div>` : '';
    if (f === 'gender') inp = `<input type="hidden" id="f_gender" value="${esc(d.gender)}"><div class="seg">${['M', 'F'].map(g => `<button type="button" class="${d.gender === g ? 'on' : ''}" onclick="setG('${g}',this)">${t(g)}</button>`).join('')}</div>`;
    else if (f === 'nid') {
      inp = `<input id="f_nid" value="${esc(d.nid)}" inputmode="numeric" maxlength="16" oninput="this.value=this.value.replace(/\\D/g,'');G('h_nid').textContent=this.value.length+'/16 digits'">`; hint = `<div class="hint" id="h_nid">${(d.nid || '').length}/16 digits</div>`;
    }
    else if (f === 'phone') inp = `<input id="f_phone" value="${esc(d.phone)}" inputmode="tel" maxlength="10" placeholder="07XXXXXXXX" oninput="this.value=this.value.replace(/\\D/g,'')">`;
    else inp = `<input id="f_${f}" value="${esc(d[f])}" ${f === 'dob' ? `type="date" max="${new Date().toISOString().slice(0, 10)}"` : ''}>`;
    return `<label for="f_${f}">${t(f)}</label>${inp}${e[f] ? `<div class="err">${e[f]}</div>` : hint}`;
  }).join('');
  return `<div class="card"><div class="row between" style="margin:0"><span class="muted">${t('step')} ${s + 1}/6</span>
    <button class="text" onclick="goRec()">${t('cancel')}</button></div>${stepper()}<h3>${t(TITLES[st.k])}</h3>${inputs}</div>
  <div class="actions">${s ? `<button class="ghost" onclick="back()">${t('back')}</button>` : ''}<button class="ghost" onclick="draftRec()">${t('savedraft')}</button>
    <button class="go" onclick="next()">${t('next')}</button></div>`;
}
function reviewHTML() {
  const sec = (k, i) => { const en = Object.entries(W.d[k] || {}).filter(x => x[1]);
  return `<div class="sec"><div class="row between" style="margin:0"><h4>${t(TITLES[k])}</h4>
    <button class="text" onclick="jump(${i})">${t('edit')}</button></div>${en.length ? `<dl>${en.map(x => `<dt>${t(x[0])}</dt>
    <dd>${esc(x[0] === 'gender' ? t(x[1]) : x[1])}</dd>`).join('')}</dl>` : '<div class="muted">-</div>'}</div>`; };
  return `<div class="card"><span class="muted">${t('step')} 6/6</span>${stepper()}<h3>${t('review')}</h3>${STEPS.map((x, i) => sec(x.k, i)).join('')}
  <label>${t('photo')}</label><input type="file" accept="image/*" capture="environment" onchange="pick(this)">${W.d.photo ? `<img class="thumb" src="${W.d.photo}" alt="ID photo">` : ''}</div>
  <div class="actions"><button class="ghost" onclick="back()">${t('back')}</button><button class="ghost" onclick="draftRec()">${t('savedraft')}</button>
    <button class="go" onclick="submitRec()">${t('submit')}</button></div>`;
}
function pick(el) {
  const f = el.files[0];
  if (!f) return;
  const img = new Image();
  img.onload = () => { const c = document.createElement('canvas'), k = Math.min(1, 480 / Math.max(img.width, img.height));
  c.width = img.width * k;
  c.height = img.height * k;
  c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
  W.d.photo = c.toDataURL('image/jpeg', .6);
  render(); };
  img.src = URL.createObjectURL(f);
}
function goNew() {
  W = { step: 0, d: {}, id: null, err: null };
  render();
}
function goRec() {
  W = null;
  render();
}
function next() {
  collect();
  const st = STEPS[W.step], e = validate(st, W.d[st.k]);
  if (Object.keys(e).length) {
    W.err = e;
    render();
    return;
  } W.err = null;
  W.step++;
  render();
}
function back() {
  collect();
  W.err = null;
  W.step--;
  render();
}
async function draftRec() {
  collect();
  if (fmtErr(W.d)) return toast(t('fix'));
  await saveRec('Draft');
  toast(t('draftsaved'));
}
async function submitRec() {
  collect();
  for (let i = 0; i < 5; i++) {
    const e = validate(STEPS[i], W.d[STEPS[i].k]);
    if (Object.keys(e).length) {
      W.step = i;
      W.err = e;
      toast(t('fix'));
      return render();
    }
  }
  await saveRec('Queued');
  toast(net() ? t('sent') : t('saved'));
}
async function saveRec(status) {
  const recs = await loadLocal(), d = W.d;
  let r = recs.find(x => x.id === W.id);
  if (!r) {
    r = { id: uid(), createdAt: new Date().toISOString(), chw: ME.id, sector: ME.sector, cell: ME.cell, village: ME.village };
    recs.push(r);
  }
  Object.assign(r, { child: d.child || {}, mother: d.mother || {}, father: d.father || {}, w1: d.w1 || {}, w2: d.w2 || {}, photo: d.photo || '', status });
  if (status === 'Queued') r.flag = '';
  await saveLocal(recs);
  W = null;
  await render();
  sync();
}
async function editRec(id) {
  const r = (await loadLocal()).find(x => x.id === id);
  W = { step: 0, id, err: null, d: { child: r.child, mother: r.mother, father: r.father, w1: r.w1, w2: r.w2, photo: r.photo } };
  render();
}
async function delRec(id) {
  await saveLocal((await loadLocal()).filter(x => x.id !== id));
  render();
}

/* FR 3.1 / 3.2: auto-sync queued records, pull registrar decisions */
async function sync(manual) {
  if (!ME || ME.role !== 'chw' || busy) return;
  if (!net()) {
    if (manual) toast(t('offnote'));
    return;
  }
  busy = true;
  try {
    const recs = await loadLocal(), db = DB();
    if (!ME) return;
    let n = 0, ch = false;
    for (const r of recs) {
      if (r.status === 'Queued') {
        if (r.sector !== ME.sector) {
          logS(db, '403 jurisdiction mismatch for ' + ME.login);
          ch = true;
          continue;
        }
        const i = db.records.findIndex(x => x.id === r.id), c = { ...r, status: 'Synced' };
        if (i < 0) db.records.push(c);
        else db.records[i] = c;
        r.status = 'Synced';
        n++;
        ch = true;
      } else if (r.status === 'Synced') {
        const s = db.records.find(x => x.id === r.id);
        if (s && (s.status === 'Approved' || s.status === 'Flagged')) {
          r.status = s.status;
          r.tracking = s.tracking;
          r.flag = s.flag;
          ch = true;
        }
      }
    }
    if (n) logS(db, `POST /sync ${n} record(s) from ${ME.login}: 200 OK`);
    if (ch) {
      S('rn_server', db);
      await saveLocal(recs);
      if (!W) render();
      if (n) toast(t('synced') + ' ' + n);
    }
  } finally {
    busy = false;
  }
}

async function chwHTML() {
  const recs = await loadLocal();
  if (!ME) return '';
  const c = k => recs.filter(r => r.status === k).length, q = c('Queued');
  const banner = net() ? '' : `<div class="banner">${t('offnote')} Records are saved on this phone and sync automatically when you reconnect.</div>`;
  const head = `<div class="phone"><div class="greet"><div><div class="muted">${t('welcome')},</div>
    <h2>${esc(ME.name.split(' ')[0])}</h2></div><span class="chip">${esc(ME.sector)} / ${esc(ME.cell)} / ${esc(ME.village)}</span>
    </div>${banner}`;
  if (W) return head + wizHTML() + '</div>';
  const list = recs.sort((a, b) => b.createdAt.localeCompare(a.createdAt)).map(r => {
    const days = Math.floor((Date.now() - new Date(r.createdAt)) / 864e5);
    return `<div class="rec" data-s="${r.status}"><div class="row between" style="margin:0">
      <b>${esc(r.child.given || '-')} ${esc(r.child.family || '')}</b><span class="badge ${r.status}">${t(r.status)}</span>
      </div>
    <div class="muted">${new Date(r.createdAt).toLocaleDateString()} - ${esc(r.mother.given || '')} ${esc(r.mother.family || '')}</div>
    ${r.tracking ? `<span class="chip big">${t('tracking')}: ${esc(r.tracking)}</span>` : ''}${r.flag ? `<div class="err">${esc(r.flag)}</div>` : ''}${r.status === 'Queued' && days >= 25 ? '<div class="err">Queued for ' + days + ' days. Connect soon (30-day limit).</div>' : ''}
    ${['Draft', 'Flagged'].includes(r.status) ? `<div class="row"><button class="ghost" onclick="editRec('${r.id}')">${t('edit')}</button>${r.status === 'Draft' ? `<button class="text" onclick="delRec('${r.id}')">${t('del')}</button>` : ''}</div>` : ''}</div>`;
  }).join('');
  return head + `<button class="cta" onclick="goNew()">+ ${t('register')}</button>${tiles([[q, t('Queued'), 'warn'], [c('Synced'), t('Synced')], [c('Approved'), t('Approved'), 'ok'], [c('Flagged'), t('Flagged'), 'bad']])}
  ${q && net() ? `<div class="row between"><span class="muted">${t('waiting')}: ${q}</span><button class="ghost" onclick="sync(true)">${t('syncnow')}</button>
    </div>` : ''}
  ${list || `<div class="empty"><h3>${t('none')}</h3><p>${t('register')}</p></div>`}</div>`;
}


/* ===== portal.js: Registrar portal and admin console ===== */
/* Sector Registrar portal + System Admin console (FR 1.2, FR 4, FR 5) */
let F = { cell: '', status: '', from: '' }, MODAL = null;
const cellOpts = sel => Object.values(GEO).flat().map(c => `<option ${c === sel ? 'selected' : ''}>${c}</option>`).join('');
const sectorOpts = sel => Object.keys(GEO).map(s => `<option ${s === sel ? 'selected' : ''}>${s}</option>`).join('');
const go = tab => { TAB = tab;
MODAL = null;
render(); };
const tabsHTML = list => `<div class="tabs">${list.map(([k, l]) => `<button class="${TAB === k ? 'on' : ''}" onclick="go('${k}')">${l}</button>`).join('')}</div>`;

function detailHTML(r) {
  const p = (title, x = {}) => { const en = Object.entries(x).filter(e => e[1]);
  return `<div class="sec"><h4>${title}</h4>${en.length ? `<dl>${en.map(e => `<dt>${t(e[0])}</dt>
    <dd>${esc(e[0] === 'gender' ? t(e[1]) : e[1])}</dd>`).join('')}</dl>` : '<div class="muted">-</div>'}</div>`; };
  const act = r.status === 'Synced' ? `<label>Comment (required to return the record)</label>
    <textarea id="fc" rows="2"></textarea><div class="row"><button onclick="decide('${r.id}',true)">Approve</button>
    <button class="bad" onclick="decide('${r.id}',false)">Return to CHW</button></div>` : (r.flag ? `<div class="err">${esc(r.flag)}</div>` : '') + (r.tracking ? `<p>${t('tracking')}: <b>${esc(r.tracking)}</b>
    </p>` : '');
  return `<div class="modal" onclick="if(event.target===this){MODAL=null;render()}"><div class="card">
    <div class="row between"><h3>Birth record</h3><span class="badge ${r.status}">${t(r.status)}</span>
    </div>
  ${p(t('child'), r.child)}${p(t('mother'), r.mother)}${p(t('father'), r.father)}${p(t('witness1'), r.w1)}${p(t('witness2'), r.w2)}
  ${r.photo ? `<img class="thumb" src="${r.photo}" alt="Parent ID photo">` : ''}${act}<button class="ghost" onclick="MODAL=null;render()">Close</button>
    </div></div>`;
}

/* FR 4.1 / 4.2 */
function regHTML() {
  const db = DB();
  let rs = db.records.filter(r => r.sector === ME.sector && ['Synced', 'Approved', 'Flagged'].includes(r.status));
  if (F.cell) rs = rs.filter(r => r.cell === F.cell);
  if (F.status) rs = rs.filter(r => r.status === F.status);
  if (F.from) rs = rs.filter(r => r.createdAt.slice(0, 10) >= F.from);
  rs.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  const tabs = tabsHTML([['rev', 'Review records'], ['cov', 'Coverage']]);
  let body;
  if (TAB === 'cov') body = covHTML(ME.sector);
  else body = `<div class="card filters"><div><label>Cell</label><select onchange="F.cell=this.value;render()">
    <option value="">All</option>${(GEO[ME.sector] || []).map(c => `<option ${F.cell === c ? 'selected' : ''}>${c}</option>`).join('')}</select>
    </div>
  <div><label>Status</label><select onchange="F.status=this.value;render()"><option value="">All</option>${['Synced', 'Approved', 'Flagged'].map(s => `<option value="${s}" ${F.status === s ? 'selected' : ''}>${t(s)}</option>`).join('')}</select>
    </div>
  <div><label>Submitted from</label><input type="date" value="${F.from}" onchange="F.from=this.value;render()">
    </div></div>
  <div class="card scroll"><table><tr><th>Child</th><th>Mother</th><th>Cell / Village</th><th>Submitted</th>
    <th>Status</th><th></th></tr>${rs.map(r => `<tr><td>${esc(r.child.given)} ${esc(r.child.family)}</td>
    <td>${esc(r.mother.given)} ${esc(r.mother.family)}</td><td>${esc(r.cell)} / ${esc(r.village)}</td>
    <td>${r.createdAt.slice(0, 10)}</td><td><span class="badge ${r.status}">${t(r.status)}</span>
    </td><td><button class="ghost" onclick="MODAL='${r.id}';render()">Open</button></td></tr>`).join('') || '<tr><td colspan="6" class="muted">No records match.</td></tr>'}</table>
    </div>`;
  const m = MODAL && db.records.find(r => r.id === MODAL);
  const all = db.records.filter(r => r.sector === ME.sector), n = k => all.filter(r => r.status === k).length;
  return `<div class="greet"><div><div class="muted">Sector registrar</div><h2>${esc(ME.name)}</h2>
    </div><span class="chip">Sector ${esc(ME.sector)}</span></div>${tiles([[n('Synced'), 'Awaiting review', 'warn'], [n('Approved'), t('Approved'), 'ok'], [n('Flagged'), 'Returned to CHW', 'bad'], [all.length, 'Total']])}${tabs}${body}${m ? detailHTML(m) : ''}`;
}
function decide(id, ok) {
  const db = DB(), r = db.records.find(x => x.id === id);
  if (ok) {
    r.status = 'Approved';
    r.flag = '';
    r.tracking = 'RN-' + new Date().getFullYear() + '-' + rnd(6);
    db.sms.unshift({ at: new Date().toISOString(), to: r.mother.phone, text: `Registration National: birth record for ${r.child.given} ${r.child.family} approved. Tracking code ${r.tracking}.` });
    /* FR 5.1 */
    logS(db, `Approved ${r.tracking} by ${ME.login}; SMS queued to ${r.mother.phone}`);
  } else {
    const c = G('fc').value.trim();
    if (!c) return toast('Add a comment so the CHW knows what to fix');
    r.status = 'Flagged';
    r.flag = c;
    logS(db, `Returned record ${r.id.slice(0, 8)} by ${ME.login}`);
  }
  S('rn_server', db);
  MODAL = null;
  render();
  toast(ok ? 'Approved. SMS sent to parent.' : 'Returned to CHW');
}

/* FR 5.2 coverage analytics by cell */
function covHTML(sec) {
  const db = DB();
  const rows = Object.entries(GEO).filter(e => !sec || e[0] === sec).flatMap(([s, cs]) => cs.map(c => {
    const rs = db.records.filter(r => r.sector === s && r.cell === c), ap = rs.filter(r => r.status === 'Approved').length;
    return { s, c, tot: rs.length, ap, pend: rs.filter(r => r.status === 'Synced').length, fl: rs.filter(r => r.status === 'Flagged').length };
  }));
  const T = rows.reduce((a, r) => ({ tot: a.tot + r.tot, ap: a.ap + r.ap }), { tot: 0, ap: 0 });
  return `<div class="card scroll"><b>Coverage by cell: ${T.ap} approved of ${T.tot} submitted</b>
    <table><tr><th>Sector</th><th>Cell</th><th>Submitted</th><th>Approved</th><th>Pending</th>
    <th>Returned</th><th>Approved rate</th></tr>${rows.map(r => { const p = r.tot ? Math.round(r.ap / r.tot * 100) : 0; return `<tr>
    <td>${r.s}</td><td>${r.c}</td><td>${r.tot}</td><td>${r.ap}</td><td>${r.pend}</td><td>${r.fl}</td>
    <td><div class="meter"><i style="width:${p}%"></i></div>${p}%</td></tr>`; }).join('')}</table>
    </div>`;
}

/* FR 1.2 + admin console */
function admHTML() {
  const db = DB();
  const tabs = tabsHTML([['usr', 'Users'], ['cov', 'Coverage'], ['sms', 'SMS log'], ['log', 'System log']]);
  let body = '';
  if (TAB === 'cov') body = covHTML('');
  else if (TAB === 'sms') body = `<div class="card scroll"><table><tr><th>Time</th><th>To</th>
    <th>Message</th></tr>${db.sms.map(s => `<tr><td>${s.at.slice(0, 16).replace('T', ' ')}</td>
    <td>${esc(s.to)}</td><td>${esc(s.text)}</td></tr>`).join('') || '<tr><td colspan="3" class="muted">No SMS sent yet. Approve a record in the registrar portal.</td></tr>'}</table>
    </div>`;
  else if (TAB === 'log') body = `<div class="card scroll"><table>${db.log.map(l => `<tr><td>${l.at.slice(0, 19).replace('T', ' ')}</td>
    <td>${esc(l.m)}</td></tr>`).join('')}</table></div>`;
  else body = `<div class="card scroll"><table><tr><th>Name</th><th>Role</th><th>Login</th><th>Sector</th>
    <th>Cell</th><th>Village</th><th></th></tr>${db.users.map(u => `<tr><td>${esc(u.name)}</td>
    <td>${u.role}</td><td>${esc(u.login)}</td>${u.role === 'admin' ? '<td colspan="4"></td>' : `<td>
    <select id="us_${u.id}">${sectorOpts(u.sector)}</select></td><td>${u.role === 'chw' ? `<select id="uc_${u.id}">${cellOpts(u.cell)}</select>` : '-'}</td>
    <td>${u.role === 'chw' ? `<input id="uv_${u.id}" value="${esc(u.village)}">` : '-'}</td>
    <td><button class="ghost" onclick="updUser('${u.id}')">Save</button> ${u.id !== ME.id ? `<button class="ghost" onclick="delUser('${u.id}')">Remove</button>` : ''}</td>`}</tr>`).join('')}</table>
    </div>
  <div class="card"><b>Create account</b><div class="filters"><div><label>Full name</label><input id="nu_n">
    </div><div><label>Role</label><select id="nu_r"><option value="chw">CHW</option><option value="registrar">Sector registrar</option>
    </select></div><div><label>Phone / username</label><input id="nu_l"></div><div><label>4-digit PIN</label>
    <input id="nu_p" maxlength="4" inputmode="numeric"></div><div><label>Sector</label><select id="nu_s">${sectorOpts('')}</select>
    </div><div><label>Cell (CHW)</label><select id="nu_c">${cellOpts('')}</select></div><div>
    <label>Village (CHW)</label><input id="nu_v"></div></div><button onclick="addUser()">Create account</button>
    </div>`;
  return `<div class="greet"><div><div class="muted">Administrator</div><h2>${esc(ME.name)}</h2>
    </div></div>${tiles([[db.users.length, 'Accounts'], [db.records.length, 'Records'], [db.records.filter(r => r.status === 'Approved').length, 'Approved', 'ok'], [db.sms.length, 'SMS sent']])}${tabs}${body}`;
}
async function addUser() {
  const db = DB(), v = id => G(id).value.trim(), login = v('nu_l'), pin = v('nu_p');
  if (!v('nu_n') || !login || !/^\d{4}$/.test(pin)) return toast('Enter a name, login and a 4-digit PIN');
  if (db.users.some(u => u.login === login)) return toast('That login already exists');
  db.users.push({ id: uid(), name: v('nu_n'), role: v('nu_r'), login, hash: await sha(login + ':' + pin), sector: v('nu_s'), cell: v('nu_c'), village: v('nu_v') });
  logS(db, 'Account created: ' + login);
  S('rn_server', db);
  refreshCache();
  render();
  toast('Account created');
}
function updUser(id) {
  const db = DB(), u = db.users.find(x => x.id === id);
  u.sector = G('us_' + id).value;
  if (u.role === 'chw') {
    u.cell = G('uc_' + id).value;
    u.village = G('uv_' + id).value.trim();
  }
  logS(db, `Jurisdiction updated for ${u.login}: ${u.sector}/${u.cell}/${u.village}`);
  S('rn_server', db);
  refreshCache();
  toast('Saved');
}
function delUser(id) {
  const db = DB();
  db.users = db.users.filter(u => u.id !== id);
  S('rn_server', db);
  refreshCache();
  render();
}


/* ===== app.js: App shell and login ===== */
/* App shell: login (offline PIN), top bar, render loop */
let ME = null, KEY = null, TAB = '';

function toast(m) {
  const el = G('toast');
  el.textContent = m;
  el.classList.add('show');
  clearTimeout(toast.t);
  toast.t = setTimeout(() => el.classList.remove('show'), 3200);
}
const LOGO = '<span class="logo"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg></span>';
const DEMOS = [['CHW', 'Gisenyi', '0788000001', '1234'], ['CHW', 'Nyamyumba', '0788000002', '2345'], ['Registrar', 'Gisenyi', 'registrar', '4321'], ['Administrator', 'All sectors', 'admin', '9999']];
function renderBar() {
  G('bar').innerHTML = `<span class="brand">${LOGO}${t('app')}</span><span class="sp"></span>
  <button class="pill ${net() ? 'on' : 'off'}" onclick="toggleNet()" title="Tap to simulate losing or regaining the network">${net() ? t('online') : t('offline')}</button>
  <select onchange="setLang(this.value)" aria-label="Language"><option value="en" ${lang === 'en' ? 'selected' : ''}>English</option>
    <option value="rw" ${lang === 'rw' ? 'selected' : ''}>Kinyarwanda</option></select>
  ${ME ? `<button class="ghost light" onclick="logout()">${t('logout')}</button>` : ''}`;
}
function loginHTML() {
  return `<section class="hero"><div class="logo big"><svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M5 12.5l4.5 4.5L19 7.5"/></svg></div><h1>${t('hero1')}</h1><p>${t('hero2')}</p>
    </section>
  <div class="card phone"><h2>${t('login')}</h2><label for="li">${t('user')}</label><input id="li" autocomplete="off">
    <label for="lp">${t('pin')}</label><input id="lp" type="password" inputmode="numeric" maxlength="4" onkeydown="if(event.key==='Enter')doLogin()">
    <div class="err" id="le"></div><button style="width:100%" onclick="doLogin()">${t('login')}</button>
    </div>
  <div class="card phone"><b>Try a demo account</b><div class="demos">${DEMOS.map(d => `<button class="demo" onclick="quick('${d[2]}','${d[3]}')">
    <b>${d[0]}</b><span>${d[1]}</span></button>`).join('')}</div>
  <p class="muted">Demo data lives in this browser only. Offline login uses credentials cached while online.</p>
    <button class="text" onclick="resetDemo()">Reset demo data</button></div>`;
}
function quick(l, p) {
  G('li').value = l;
  G('lp').value = p;
  doLogin();
}
async function doLogin() {
  const id = G('li').value.trim(), pin = G('lp').value;
  const u = J('rn_cred', []).find(x => x.login === id);
  if (!u || u.hash !== await sha(id + ':' + pin)) {
    G('le').textContent = 'Wrong phone/username or PIN.' + (net() ? '' : ' Offline login only works for accounts cached on this device.');
    return;
  }
  ME = u;
  KEY = await deriveKey(pin, 'rn:' + u.id);
  W = null;
  MODAL = null;
  TAB = u.role === 'registrar' ? 'rev' : u.role === 'admin' ? 'usr' : '';
  render();
  sync();
}
function logout() {
  ME = KEY = W = MODAL = null;
  render();
}
function toggleNet() {
  LS.setItem('rn_net', net() ? 'off' : 'on');
  refreshCache();
  render();
  if (net()) sync();
}
function setLang(l) {
  lang = l;
  LS.setItem('rn_lang', l);
  document.documentElement.lang = l;
  render();
}
function resetDemo() {
  if (apiOK) xhr('POST', '/api/reset', '{}');
  Object.keys(LS).filter(k => k.startsWith('rn_') && k !== 'rn_lang').forEach(k => LS.removeItem(k));
  location.reload();
}

async function render() {
  renderBar();
  const app = G('app');
  if (!ME) {
    app.innerHTML = loginHTML();
    return;
  }
  if (ME.role === 'chw') {
    const h = await chwHTML();
    if (ME) app.innerHTML = h;
    else render();
  }
  else if (!net()) app.innerHTML = '<div class="card phone"><h3>Offline</h3><p>The registrar and admin portals need a connection. Switch the network toggle back to Online.</p></div>';
  else app.innerHTML = ME.role === 'registrar' ? regHTML() : admHTML();
}

setInterval(() => { if (ME && ME.role === 'chw') sync(); }, 4000);
seed().then(() => { refreshCache(); render(); });
</script>
</body>
</html>
'''

# ---------------------------------------------------------------------------
# Database (SQLite key/value store holding the shared server state as JSON)
# ---------------------------------------------------------------------------
def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    return conn


def load_state():
    with LOCK, closing(connect()) as conn:
        row = conn.execute("SELECT value FROM kv WHERE key = 'server'").fetchone()
        return row[0] if row else None


def save_state(text):
    with LOCK, closing(connect()) as conn, conn:
        conn.execute("INSERT OR REPLACE INTO kv (key, value) VALUES ('server', ?)", (text,))


def reset_state():
    with LOCK, closing(connect()) as conn, conn:
        conn.execute("DELETE FROM kv")


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body=b"", ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif path == "/api/ping":
            self._send(200, '{"ok": true}')
        elif path == "/api/db":
            state = load_state()
            if state is None:
                self._send(404, '{"error": "empty"}')
            else:
                self._send(200, state)
        else:
            self._send(404, '{"error": "not found"}')

    def do_POST(self):
        path = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self._send(413, '{"error": "too large"}')
        raw = self.rfile.read(length)
        if path == "/api/db":
            try:
                data = json.loads(raw)
                assert isinstance(data, dict) and "users" in data and "records" in data
            except (ValueError, AssertionError):
                return self._send(400, '{"error": "invalid database"}')
            save_state(json.dumps(data))
            self._send(200, '{"ok": true}')
        elif path == "/api/reset":
            reset_state()
            self._send(200, '{"ok": true}')
        else:
            self._send(404, '{"error": "not found"}')

    def log_message(self, fmt, *args):
        if "/api/" not in self.path:
            print("  %s - %s" % (self.address_string(), fmt % args))


def lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def main():
    parser = argparse.ArgumentParser(description="Registration National prototype server")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("Registration National is running")
    print("  Local:   http://127.0.0.1:%d" % args.port)
    if args.host == "0.0.0.0":
        print("  Network: http://%s:%d" % (lan_ip(), args.port))
    print("  Data:    %s" % DB_FILE)
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()