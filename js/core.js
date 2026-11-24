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

/* Jurisdictions: the full national hierarchy (province, district, sector, cell) lives in js/geo.js */

/* i18n: Kinyarwanda + English (NFR 4 / 6.5) */
const L = {
  en: { app: 'Registration National', welcome: 'Welcome', hero1: 'Every birth counted, even offline.', hero2: 'Register newborns at home, sync later, and send parents a tracking code by SMS.', register: 'Register a newborn', cancel: 'Cancel', login: 'Sign in', user: 'Phone number or username', pin: 'PIN', logout: 'Log out', online: 'Online', offline: 'Offline', records: 'My records', newrec: 'New birth record', step: 'Step', child: 'Child', mother: 'Mother', father: 'Father (optional)', witness1: 'Witness 1', witness2: 'Witness 2 (optional)', given: 'Given name', family: 'Family name', dob: 'Date of birth', pob: 'Place of birth', gender: 'Gender', M: 'Male', F: 'Female', nid: 'National ID (16 digits)', phone: 'Phone (07XXXXXXXX)', address: 'Address', next: 'Next', back: 'Back', savedraft: 'Save draft', submit: 'Submit', review: 'Review and submit', photo: 'Photo of parent ID (optional)', none: 'No records yet', tracking: 'Tracking code', edit: 'Edit', del: 'Delete', syncnow: 'Sync now', waiting: 'Waiting to sync', req: 'Required', nid16: 'ID must be 16 digits', phbad: 'Use format 07XXXXXXXX', dobfut: 'Date cannot be in the future', fix: 'Fix the highlighted fields', saved: 'Saved offline. It will sync when you are online.', sent: 'Submitted and synced', draftsaved: 'Draft saved', offnote: 'You are offline. Records stay queued.', synced: 'Synced records:', Draft: 'Draft', Queued: 'Queued', Synced: 'Synced', Approved: 'Approved', Flagged: 'Needs correction' },
  rw: { welcome: 'Murakaza neza', hero1: 'Buri mwana wese yandikwe, nubwo nta interineti.', hero2: 'Andika abana bavutse mu ngo, wohereze nyuma, ababyeyi bahabwe kode ikurikirana kuri SMS.', register: 'Andika umwana mushya', cancel: 'Reka', login: 'Injira', user: 'Telefone cyangwa izina', pin: "Umubare w'ibanga", logout: 'Sohoka', online: 'Hari interineti', offline: 'Nta interineti', records: 'Inyandiko zanjye', newrec: 'Andika umwana mushya', step: 'Intambwe', child: 'Umwana', mother: 'Mama', father: 'Papa (si ngombwa)', witness1: 'Umutangabuhamya 1', witness2: 'Umutangabuhamya 2 (si ngombwa)', given: 'Izina bwite', family: "Izina ry'umuryango", dob: "Itariki y'amavuko", pob: 'Aho yavukiye', gender: 'Igitsina', M: 'Gabo', F: 'Gore', nid: 'Indangamuntu (imibare 16)', phone: 'Telefone', address: 'Aho atuye', next: 'Komeza', back: 'Subira inyuma', savedraft: "Bika nk'inyandiko", submit: 'Ohereza', review: 'Kureba no kohereza', none: 'Nta nyandiko zihari', tracking: 'Kode ikurikirana', edit: 'Hindura', del: 'Siba', syncnow: 'Ohereza ubu', waiting: 'Zitegereje kohereza', req: 'Bikenewe', nid16: 'Indangamuntu igomba kuba imibare 16', Draft: 'Inyandiko', Queued: 'Mu murongo', Synced: 'Byoherejwe', Approved: 'Byemejwe', Flagged: 'Bikosorwe' }
};
/* Additional UI text (portal, dashboards, messages) */
Object.assign(L.en, {
  "dashboard": "Dashboard",
  "reviewrec": "Review records",
  "coverage": "Coverage",
  "users": "Users",
  "smslog": "SMS log",
  "allopt": "All",
  "cell": "Cell",
  "status": "Status",
  "subfrom": "Submitted from",
  "cellvillage": "Cell / Village",
  "submitted": "Submitted",
  "open": "Open",
  "nomatch": "No records match.",
  "sector": "Sector",
  "village": "Village",
  "birthrec": "Birth record",
  "commentreq": "Comment (required to return the record)",
  "approve": "Approve",
  "returnchw": "Return to CHW",
  "close": "Close",
  "needcomment": "Add a comment so the CHW knows what to fix",
  "approvedsms": "Approved. SMS sent to parent.",
  "returned": "Returned to CHW",
  "covtitle": "Coverage by cell: {a} approved of {t} submitted",
  "pending": "Pending",
  "retshort": "Returned",
  "apprate": "Approved rate",
  "recsub": "Records submitted",
  "awaiting": "Awaiting review",
  "returnedchw": "Returned to CHW",
  "approvalrate": "Approval rate",
  "accounts": "Accounts",
  "smssent": "SMS sent",
  "startTitle": "Getting started",
  "start1": "Open <b>Users</b> and create a Sector registrar and a CHW (choose their sector, cell and village).",
  "start2": "Sign in as the CHW and register a newborn.",
  "start3": "Sign in as the registrar to review and approve it.",
  "last7": "Submissions, last 7 days",
  "recstatus": "Record status",
  "busiest": "Busiest cells",
  "norecyet": "No records yet.",
  "recent": "Recent records",
  "nothingsub": "Nothing submitted yet.",
  "time": "Time",
  "to": "To",
  "message": "Message",
  "nosms": "No SMS sent yet. Approve a record in the registrar portal.",
  "name": "Name",
  "role": "Role",
  "loginlbl": "Login",
  "save": "Save",
  "remove": "Remove",
  "createacct": "Create account",
  "fullname": "Full name",
  "phoneuser": "Phone / username",
  "pin4": "4-digit PIN",
  "cellchw": "Cell (CHW)",
  "villagechw": "Village (CHW)",
  "role_chw": "CHW",
  "role_registrar": "Sector registrar",
  "role_admin": "Administrator",
  "userbad": "Enter a name, login and a 4-digit PIN",
  "dup": "That login already exists",
  "created": "Account created",
  "savedok": "Saved",
  "smstext": "Registration National: birth record for {name} approved. Tracking code {code}.",
  "offbanner": "You are offline. Records are saved on this phone and sync automatically when you reconnect.",
  "oldq": "Queued for {n} days. Connect soon (30-day limit).",
  "hint_pob": "Village or health facility",
  "hint_phone": "We send the tracking code to this number by SMS",
  "thisweek": "This week",
  "accnote": "Accounts are created by your administrator.",
  "wrongcred": "Wrong phone/username or PIN.",
  "wrongoff": " Offline sign-in only works for accounts used on this device.",
  "offtext": "The registrar and admin portals need a connection. Switch the network toggle back to Online.",
  "nettip": "Tap to simulate losing or regaining the network"
});
Object.assign(L.rw, {
  "dashboard": "Imbonerahamwe",
  "reviewrec": "Gusuzuma inyandiko",
  "coverage": "Ingano y'iyandikishwa",
  "users": "Abakoresha",
  "smslog": "Ubutumwa bwa SMS",
  "allopt": "Byose",
  "cell": "Akagari",
  "status": "Imiterere",
  "subfrom": "Zoherejwe guhera",
  "cellvillage": "Akagari / Umudugudu",
  "submitted": "Yoherejwe",
  "open": "Fungura",
  "nomatch": "Nta nyandiko zihuye.",
  "sector": "Umurenge",
  "village": "Umudugudu",
  "birthrec": "Inyandiko y'ivuka",
  "commentreq": "Ibisobanuro (bikenewe mu gusubiza inyandiko)",
  "approve": "Emeza",
  "returnchw": "Subiza umujyanama",
  "close": "Funga",
  "needcomment": "Andika ibisobanuro kugira ngo umujyanama amenye icyo akosora",
  "approvedsms": "Byemejwe. SMS yoherejwe ku mubyeyi.",
  "returned": "Yasubijwe umujyanama",
  "covtitle": "Ingano ku kagari: {a} byemejwe muri {t} byoherejwe",
  "pending": "Zitegereje",
  "retshort": "Zasubijwe",
  "apprate": "Igipimo cy'ibyemejwe",
  "recsub": "Inyandiko zoherejwe",
  "awaiting": "Zitegereje gusuzumwa",
  "returnedchw": "Zasubijwe umujyanama",
  "approvalrate": "Igipimo cy'ibyemejwe",
  "accounts": "Konti",
  "smssent": "SMS zoherejwe",
  "startTitle": "Tangirira hano",
  "start1": "Fungura <b>Abakoresha</b> maze ukore konti y'umwanditsi w'irangamimerere n'iy'umujyanama w'ubuzima (uhitemo umurenge, akagari n'umudugudu).",
  "start2": "Injira nk'umujyanama w'ubuzima maze wandike umwana wavutse.",
  "start3": "Injira nk'umwanditsi w'irangamimerere kugira ngo usuzume kandi wemeze inyandiko.",
  "last7": "Inyandiko zoherejwe mu minsi 7 ishize",
  "recstatus": "Uko inyandiko zihagaze",
  "busiest": "Utugari dufite inyandiko nyinshi",
  "norecyet": "Nta nyandiko zihari.",
  "recent": "Inyandiko za vuba",
  "nothingsub": "Nta nyandiko ziroherezwa.",
  "time": "Igihe",
  "to": "Kuri",
  "message": "Ubutumwa",
  "nosms": "Nta SMS iroherezwa. Emeza inyandiko ku rubuga rw'umwanditsi.",
  "name": "Izina",
  "role": "Uruhare",
  "loginlbl": "Telefone / izina",
  "save": "Bika",
  "remove": "Kuraho",
  "createacct": "Kora konti",
  "fullname": "Amazina yombi",
  "phoneuser": "Telefone / izina",
  "pin4": "Umubare w'ibanga (imibare 4)",
  "cellchw": "Akagari (umujyanama)",
  "villagechw": "Umudugudu (umujyanama)",
  "role_chw": "Umujyanama w'ubuzima",
  "role_registrar": "Umwanditsi w'irangamimerere",
  "role_admin": "Umuyobozi wa sisitemu",
  "userbad": "Andika izina, telefone cyangwa izina ry'ukoresha, n'umubare w'ibanga w'imibare 4",
  "dup": "Iyo konti isanzwe ihari",
  "created": "Konti yakozwe",
  "savedok": "Byabitswe",
  "smstext": "Registration National: inyandiko y'ivuka ya {name} yemejwe. Kode ikurikirana: {code}.",
  "offbanner": "Nta interineti. Inyandiko zibikwa kuri telefone kandi zoherezwa ubwazo interineti nigaruka.",
  "oldq": "Mu murongo hashize iminsi {n}. Shaka interineti vuba (imipaka ni iminsi 30).",
  "hint_pob": "Umudugudu cyangwa ikigo nderabuzima",
  "hint_phone": "Kode ikurikirana izoherezwa kuri iyi telefone kuri SMS",
  "thisweek": "Iki cyumweru",
  "accnote": "Konti zikorwa n'umuyobozi wa sisitemu.",
  "wrongcred": "Telefone cyangwa izina cyangwa umubare w'ibanga si byo.",
  "wrongoff": " Nta interineti: winjira gusa ukoresheje konti zigeze gukoreshwa kuri iki gikoresho.",
  "offtext": "Urubuga rw'umwanditsi n'urw'umuyobozi bikenera interineti. Subiza interineti kuri \"Hari interineti\".",
  "nettip": "Kanda kugira ngo wigane gutakaza cyangwa kongera kubona interineti"
});
Object.assign(L.rw, {
  "app": "Registration National",
  "photo": "Ifoto y'indangamuntu y'umubyeyi (si ngombwa)",
  "phbad": "Koresha imiterere 07XXXXXXXX",
  "dobfut": "Itariki ntishobora kuba mu gihe kizaza",
  "fix": "Kosora ibyagaragajwe",
  "saved": "Byabitswe nta interineti. Bizoherezwa interineti nigaruka.",
  "sent": "Byoherejwe",
  "draftsaved": "Inyandiko yabitswe",
  "offnote": "Nta interineti. Inyandiko ziguma mu murongo.",
  "synced": "Byoherejwe:"
});
Object.assign(L.en, {
  "province": "Province",
  "district": "District",
  "sectors": "Sectors",
  "cells": "Cells",
  "pickdistrict": "Select district",
  "picksector": "Select sector",
  "pickcell": "Select cell",
  "needgeo": "Choose a district and sector (and a cell for a CHW)",
  "covnational": "National coverage: {a} approved of {t} submitted",
  "covscope": "Showing {c} cells",
  "covdrill": "Select a district to see its sectors and cells.",
  "covall": "All districts",
  "covback": "Back to all districts",
  "geoinfo": "{d} districts, {s} sectors, {c} cells"
});
Object.assign(L.rw, {
  "province": "Intara",
  "district": "Akarere",
  "sectors": "Imirenge",
  "cells": "Utugari",
  "pickdistrict": "Hitamo akarere",
  "picksector": "Hitamo umurenge",
  "pickcell": "Hitamo akagari",
  "needgeo": "Hitamo akarere n'umurenge (n'akagari ku mujyanama w'ubuzima)",
  "covnational": "Ingano mu gihugu: {a} byemejwe muri {t} byoherejwe",
  "covscope": "Hagaragajwe utugari {c}",
  "covdrill": "Hitamo akarere urebe imirenge n'utugari twaryo.",
  "covall": "Uturere twose",
  "covback": "Subira ku turere twose",
  "geoinfo": "Uturere {d}, imirenge {s}, utugari {c}"
});
L.en.offtitle = 'Offline';
L.rw.offtitle = 'Nta interineti';
const WEEKDAYS_RW = ['Cyu', 'Mbe', 'Kab', 'Gat', 'Kan', 'Gnu', 'Gnd'];

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
/* First run: create one bootstrap administrator (admin / 1234). The admin then creates every other account (FR 1.2). */
/* Older data stored only a sector name. Add the district when that sector name belongs to exactly one district. */
function migrateGeo(db) {
  let changed = false;
  const fix = x => {
    const ds = x && x.sector && !x.district && SECTOR_DISTRICTS[x.sector];
    if (ds && ds.length === 1) {
      x.district = ds[0];
      changed = true;
    }
  };
  db.users.forEach(fix);
  db.records.forEach(fix);
  return changed;
}
async function seed() {
  const existing = DB();
  if (existing) {
    if (migrateGeo(existing)) S('rn_server', existing);
    return;
  }
  const db = {
    users: [{ id: 'u-admin', name: 'Administrator', role: 'admin', login: 'admin', hash: await sha('admin:1234'), district: '', sector: '', cell: '', village: '' }],
    records: [], sms: [], log: []
  };
    /* Demo accounts, recreated whenever the database starts empty (for example after the free Render service restarts) */
  const DEMO = [
    { id: 'u-demo-registrar', name: 'eddy', role: 'registrar', login: '0788123987', pin: '2222', district: 'Nyarugenge', sector: 'Nyamirambo', cell: '', village: '' },
    { id: 'u-demo-chw', name: 'loic', role: 'chw', login: '0798123456', pin: '1111', district: 'Nyarugenge', sector: 'Nyamirambo', cell: 'Mumena', village: '' }
  ];
  for (const { pin, ...u } of DEMO) db.users.push({ ...u, hash: await sha(u.login + ':' + pin) });
  logS(db, 'System initialised');
  S('rn_server', db);
}

/* Refresh the offline credential cache whenever the device is online (FR 1.1) */
function refreshCache() {
  const db = DB();
  if (net() && db) S('rn_cred', db.users);
}

const tiles = l => `<div class="tiles">${l.map(x => `<div class="tile ${x[2] || ''}"><b>${x[0]}</b>
  <span>${x[1]}</span></div>`).join('')}</div>`;

/* Submissions per day for the last 7 days (shared by the CHW and portal dashboards) */
const weekChart = rs => {
  const days = Array.from({ length: 7 }, (_, i) => new Date(Date.now() - (6 - i) * 864e5).toISOString().slice(0, 10));
  const per = days.map(d => rs.filter(r => (r.createdAt || '').slice(0, 10) === d).length);
  const max = Math.max(1, ...per);
  return `<div class="bars">${days.map((d, i) => `<div class="bcol"><b>${per[i]}</b><div class="bw"><i style="height:${per[i] / max * 100}%"></i></div><small>${(lang === 'rw' ? WEEKDAYS_RW[new Date(d + 'T12:00:00').getDay()] : new Date(d + 'T12:00:00').toLocaleDateString(undefined, { weekday: 'short' }))}</small></div>`).join('')}</div>`;
};
