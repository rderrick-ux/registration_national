/* ============================================================
   CORE: state, helpers, translations, storage, encryption, seed
   ============================================================ */

/* ---------- Shared application state ---------- */
let ME = null;      // signed-in user
let KEY = null;     // AES key derived from the user's PIN (CHW offline queue)
let AUTH = '';      // landing screen: '' | 'in' | 'up'
let TAB = '';       // active tab in registrar / admin consoles
let W = null;       // CHW wizard state
let MODAL = null;   // open record id in registrar portal
let busy = false;   // sync lock
let F = { cell: '', status: '', from: '' };   // registrar filters

/* ---------- Helpers ---------- */
const G = id => document.getElementById(id);
const LS = localStorage;
const J = (k, d) => { try { return JSON.parse(LS.getItem(k)) ?? d; } catch { return d; } };
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const uid = () => crypto.randomUUID();
const rnd = n => Array.from({ length: n }, () => Math.floor(Math.random() * 10)).join('');
const nidOK = v => /^\d{16}$/.test(v || '');
const phOK = v => /^07[2389]\d{7}$/.test(v || '');
const net = () => LS.getItem('rn_net') !== 'off';
const logS = (db, m) => { db.log.unshift({ at: new Date().toISOString(), m }); db.log.length = Math.min(db.log.length, 100); };

const tiles = list => `<div class="tiles">${list.map(x =>
  `<div class="tile ${x[2] || ''}"><b>${x[0]}</b><span>${x[1]}</span></div>`).join('')}</div>`;

function toast(m) {
  const el = G('toast');
  el.textContent = m;
  el.classList.add('show');
  clearTimeout(toast.t);
  toast.t = setTimeout(() => el.classList.remove('show'), 3200);
}

/* ---------- Jurisdictions: province > district > sector > cell (data in rwanda.js) ---------- */
const geoProvinces = () => Object.keys(RWANDA);
const geoDistricts = p => Object.keys(RWANDA[p] || {});
const geoSectors = (p, d) => Object.keys((RWANDA[p] || {})[d] || {});
const geoCells = (p, d, s) => ((RWANDA[p] || {})[d] || {})[s] || [];
const geoList = (items, sel) => items.map(x => `<option ${x === sel ? 'selected' : ''}>${esc(x)}</option>`).join('');

/* Cascading selects. Returns one HTML string per field so callers can wrap them (card, grid or table cell).
   Ids are <prefix>_p, _d, _s, _c (use a prefix like geo_x so they never clash with other field ids). Pass { cell: false } for roles without a cell, { labels: false } inside tables. */
function geoFields(px, sel = {}, o = {}) {
  const p = RWANDA[sel.province] ? sel.province : geoProvinces()[0];
  const d = geoDistricts(p).includes(sel.district) ? sel.district : geoDistricts(p)[0];
  const s = geoSectors(p, d).includes(sel.sector) ? sel.sector : geoSectors(p, d)[0];
  const c = geoCells(p, d, s).includes(sel.cell) ? sel.cell : geoCells(p, d, s)[0];
  const field = (lvl, key, items, cur) =>
    (o.labels === false ? '' : `<label for="${px}_${lvl}">${t(key)}</label>`) +
    `<select id="${px}_${lvl}" onchange="geoChange('${px}','${lvl}')">${geoList(items, cur)}</select>`;
  const out = [field('p', 'province', geoProvinces(), p), field('d', 'district', geoDistricts(p), d), field('s', 'sector', geoSectors(p, d), s)];
  if (o.cell !== false) out.push(field('c', 'cell', geoCells(p, d, s), c));
  return out;
}
/* Refill the lower levels when a higher one changes */
function geoChange(px, lvl) {
  const v = l => { const el = G(px + '_' + l); return el ? el.value : ''; };
  const fill = (l, items) => { const el = G(px + '_' + l); if (el) el.innerHTML = geoList(items, ''); };
  if (lvl === 'p') fill('d', geoDistricts(v('p')));
  if (lvl === 'p' || lvl === 'd') fill('s', geoSectors(v('p'), v('d')));
  if (lvl !== 'c') fill('c', geoCells(v('p'), v('d'), v('s')));
}
const geoVal = px => ({ province: (G(px + '_p') || {}).value || '', district: (G(px + '_d') || {}).value || '',
  sector: (G(px + '_s') || {}).value || '', cell: (G(px + '_c') || {}).value || '' });
/* A record belongs to a user's sector when district and sector both match */
const sameSector = (a, b) => a.district === b.district && a.sector === b.sector;

/* ---------- Storage: shared SQLite via the Python server, else this browser's localStorage ---------- */
function xhr(method, url, body) {
  const x = new XMLHttpRequest();
  x.open(method, url, false);
  if (body) x.setRequestHeader('Content-Type', 'application/json');
  x.send(body || null);
  return x;
}
const apiOK = (() => { try { return xhr('GET', '/api/ping').status === 200; } catch { return false; } })();

/* S writes a value; the shared database key goes to the server when available */
const S = (k, v) => {
  if (k === 'rn_server' && apiOK) xhr('POST', '/api/db', JSON.stringify(v));
  else LS.setItem(k, JSON.stringify(v));
};
/* DB reads the shared database (null until seeded) */
const DB = () => {
  if (!apiOK) return J('rn_server', null);
  const x = xhr('GET', '/api/db');
  return x.status === 200 ? JSON.parse(x.responseText) : null;
};
/* Keep a local copy of credentials so CHWs can sign in while offline */
function refreshCache() {
  const db = DB();
  if (net() && db) S('rn_cred', db.users);
}

/* ---------- Translations: English + Kinyarwanda ---------- */
const L = {
  en: {
    app: 'Registration National', footer: 'Registration National prototype. Demo data only; no real NIDA or SMS integration.',
    welcome: 'Welcome', hero1: 'Every birth counted, even offline.',
    hero2: 'Register newborns at home, sync later, and send parents a tracking code by SMS.',
    /* auth */
    signin: 'Sign in', signup: 'Sign up', create: 'Create account', logout: 'Log out',
    user: 'Phone number or username', pin: 'PIN', pin4: 'PIN must be 4 digits', name: 'Full name',
    haveacc: 'Already have an account?', noacc: 'New here?', back2: 'Back',
    exists: 'That phone number is already registered', needNet: 'Go online to sign up',
    wrong: 'Wrong phone/username or PIN.', wrongOff: ' Offline sign in only works for accounts cached on this device.',
    demo: 'Try a demo account', reset: 'Reset demo data',
    demoNote: 'Demo data is shared through the local server. Offline sign in uses credentials cached while online.',
    /* top bar / dashboard */
    online: 'Online', offline: 'Offline', netTip: 'Tap to simulate losing or regaining the network',
    dash: 'Dashboard', language: 'Language',
    offlinePortal: 'The registrar and admin portals need a connection. Switch the network toggle back to Online.',
    /* CHW */
    register: 'Register a newborn', cancel: 'Cancel', step: 'Step', child: 'Child', mother: 'Mother',
    father: 'Father (optional)', witness1: 'Witness 1', witness2: 'Witness 2 (optional)',
    given: 'Given name', family: 'Family name', dob: 'Date of birth', pob: 'Place of birth', gender: 'Gender',
    M: 'Male', F: 'Female', nid: 'National ID (16 digits)', phone: 'Phone (07XXXXXXXX)', address: 'Address',
    next: 'Next', back: 'Back', savedraft: 'Save draft', submit: 'Submit', review: 'Review and submit',
    photo: 'Photo of parent ID (optional)', none: 'No records yet', tracking: 'Tracking code',
    edit: 'Edit', del: 'Delete', syncnow: 'Sync now', waiting: 'Waiting to sync',
    req: 'Required', nid16: 'ID must be 16 digits', phbad: 'Use format 07XXXXXXXX',
    dobfut: 'Date cannot be in the future', fix: 'Fix the highlighted fields',
    saved: 'Saved offline. It will sync when you are online.', sent: 'Submitted and synced',
    draftsaved: 'Draft saved', offnote: 'You are offline. Records are saved on this phone and sync automatically when you reconnect.',
    synced: 'Synced records:', hintPob: 'Village or health facility', hintPhone: 'We send the tracking code to this number by SMS',
    digits: 'digits', queuedWarn: 'Queued for {n} days. Connect soon (30-day limit).',
    Draft: 'Draft', Queued: 'Queued', Synced: 'Synced', Approved: 'Approved', Flagged: 'Needs correction',
    /* registrar / admin */
    regrole: 'Sector registrar', adminrole: 'Administrator', province: 'Province', district: 'District', sector: 'Sector', cell: 'Cell', village: 'Village',
    rev: 'Review records', cov: 'Coverage', await: 'Awaiting review', returned: 'Returned to CHW', total: 'Total',
    status: 'Status', all: 'All', from: 'Submitted from', submitted: 'Submitted', none2: 'No records match.',
    open: 'Open', close: 'Close', approve: 'Approve', returnchw: 'Return to CHW', record: 'Birth record',
    comment: 'Comment (required to return the record)', needComment: 'Add a comment so the CHW knows what to fix',
    okApproved: 'Approved. SMS sent to parent.', okReturned: 'Returned to CHW',
    covTitle: 'Coverage by cell: {a} approved of {t} submitted', pending: 'Pending', approvedRate: 'Approved rate',
    users: 'Users', accounts: 'Accounts', records: 'Records', smsSent: 'SMS sent', smslog: 'SMS log', syslog: 'System log',
    time: 'Time', to: 'To', msg: 'Message', noSms: 'No SMS sent yet. Approve a record in the registrar portal.',
    role: 'Role', login: 'Login', save: 'Save', remove: 'Remove', createAcct: 'Create account',
    roleChw: 'CHW', phoneUser: 'Phone / username', pinLabel: '4-digit PIN', cellNote: 'Cell and village apply to CHWs only.', villageChw: 'Village (CHW)',
    needFields: 'Enter a name, login and a 4-digit PIN', loginUsed: 'That login already exists',
    acctCreated: 'Account created', savedOk: 'Saved'
  },
  rw: {
    app: 'Registration National', footer: 'Registration National (ikigeragezo). Amakuru y’ikitegererezo gusa; nta NIDA cyangwa SMS nyakuri.',
    welcome: 'Murakaza neza', hero1: 'Buri mwana wese yandikwe, nubwo nta interineti.',
    hero2: 'Andika abana bavutse mu ngo, wohereze nyuma, ababyeyi bahabwe kode ikurikirana kuri SMS.',
    signin: 'Injira', signup: 'Iyandikishe', create: 'Fungura konti', logout: 'Sohoka',
    user: 'Telefone cyangwa izina', pin: "Umubare w'ibanga", pin4: "Umubare w'ibanga ugomba kuba imibare 4", name: 'Amazina yombi',
    haveacc: 'Usanzwe ufite konti?', noacc: 'Uri mushya?', back2: 'Subira inyuma',
    exists: 'Iyi telefone isanzwe yanditse', needNet: 'Banza ubone interineti',
    wrong: "Telefone cyangwa umubare w'ibanga si byo.", wrongOff: ' Nta interineti: winjira gusa ku konti zabitswe kuri iki gikoresho.',
    demo: 'Gerageza konti y’ikitegererezo', reset: 'Siba amakuru y’ikitegererezo',
    demoNote: 'Amakuru y’ikitegererezo abitswa kuri seriveri. Nta interineti, winjira ukoresheje konti zabitswe.',
    online: 'Hari interineti', offline: 'Nta interineti', netTip: 'Kanda kugerageza kubura cyangwa kubona interineti',
    dash: 'Imbonerahamwe', language: 'Ururimi',
    offlinePortal: 'Umwanditsi n’umuyobozi bakeneye interineti. Subiza interineti kuri Hari interineti.',
    register: 'Andika umwana mushya', cancel: 'Reka', step: 'Intambwe', child: 'Umwana', mother: 'Mama',
    father: 'Papa (si ngombwa)', witness1: 'Umutangabuhamya 1', witness2: 'Umutangabuhamya 2 (si ngombwa)',
    given: 'Izina bwite', family: "Izina ry'umuryango", dob: "Itariki y'amavuko", pob: 'Aho yavukiye', gender: 'Igitsina',
    M: 'Gabo', F: 'Gore', nid: 'Indangamuntu (imibare 16)', phone: 'Telefone (07XXXXXXXX)', address: 'Aho atuye',
    next: 'Komeza', back: 'Subira inyuma', savedraft: "Bika nk'inyandiko", submit: 'Ohereza', review: 'Kureba no kohereza',
    photo: "Ifoto y'indangamuntu y'umubyeyi (si ngombwa)", none: 'Nta nyandiko zihari', tracking: 'Kode ikurikirana',
    edit: 'Hindura', del: 'Siba', syncnow: 'Ohereza ubu', waiting: 'Zitegereje kohereza',
    req: 'Bikenewe', nid16: 'Indangamuntu igomba kuba imibare 16', phbad: 'Koresha 07XXXXXXXX',
    dobfut: 'Itariki ntishobora kuba mu gihe kizaza', fix: 'Kosora ibigaragara',
    saved: 'Byabitswe. Bizoherezwa ubonye interineti.', sent: 'Byoherejwe',
    draftsaved: 'Inyandiko yabitswe', offnote: 'Nta interineti. Inyandiko zibitswe kuri telefone kandi zizoherezwa ubonye interineti.',
    synced: 'Byoherejwe:', hintPob: 'Umudugudu cyangwa ivuriro', hintPhone: 'Kode ikurikirana izoherezwa kuri iyi telefone kuri SMS',
    digits: 'imibare', queuedWarn: 'Imaze iminsi {n} itegereje. Shaka interineti vuba (imipaka ni iminsi 30).',
    Draft: 'Inyandiko', Queued: 'Mu murongo', Synced: 'Byoherejwe', Approved: 'Byemejwe', Flagged: 'Bikosorwe',
    regrole: "Umwanditsi w'umurenge", adminrole: 'Umuyobozi', province: 'Intara', district: 'Akarere', sector: 'Umurenge', cell: 'Akagari', village: 'Umudugudu',
    rev: 'Suzuma inyandiko', cov: 'Uko bihagaze', await: 'Zitegereje gusuzumwa', returned: 'Zasubijwe umukozi', total: 'Zose',
    status: 'Imiterere', all: 'Byose', from: 'Zoherejwe guhera', submitted: 'Yoherejwe', none2: 'Nta nyandiko zibonetse.',
    open: 'Fungura', close: 'Funga', approve: 'Emeza', returnchw: 'Subiza umukozi', record: "Inyandiko y'amavuko",
    comment: 'Igitekerezo (gikenewe mu gusubiza inyandiko)', needComment: 'Andika igitekerezo kugira ngo umukozi amenye icyo akosora',
    okApproved: 'Byemejwe. SMS yoherejwe ku mubyeyi.', okReturned: 'Yasubijwe umukozi',
    covTitle: 'Uko bihagaze mu tugari: {a} byemejwe muri {t} byoherejwe', pending: 'Zitegereje', approvedRate: 'Ijanisha ryemejwe',
    users: 'Abakoresha', accounts: 'Konti', records: 'Inyandiko', smsSent: 'SMS zoherejwe', smslog: 'Amateka ya SMS', syslog: 'Amateka ya sisitemu',
    time: 'Igihe', to: 'Kuri', msg: 'Ubutumwa', noSms: 'Nta SMS irohereza. Emeza inyandiko mu rubuga rw’umwanditsi.',
    role: 'Uruhare', login: 'Kwinjira', save: 'Bika', remove: 'Kuraho', createAcct: 'Fungura konti',
    roleChw: 'Umujyanama w’ubuzima', phoneUser: 'Telefone / izina', pinLabel: "Umubare w'ibanga (4)", cellNote: 'Akagari n’umudugudu bireba abajyanama gusa.', villageChw: 'Umudugudu (umujyanama)',
    needFields: "Andika izina, uko winjira n'umubare w'ibanga 4", loginUsed: 'Uku kwinjira kusanzwe gukoreshwa',
    acctCreated: 'Konti yafunguwe', savedOk: 'Byabitswe'
  }
};
let lang = LS.getItem('rn_lang') || 'en';
const t = k => (L[lang] && L[lang][k]) || L.en[k] || k;

/* ---------- Encryption: AES-256-GCM, key from PIN via PBKDF2 (stand-in for SQLCipher on a phone) ---------- */
const enc = new TextEncoder(), dec = new TextDecoder();
const b64 = b => { let s = ''; for (const x of new Uint8Array(b)) s += String.fromCharCode(x); return btoa(s); };
const unb64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
const sha = async s => b64(await crypto.subtle.digest('SHA-256', enc.encode(s)));

async function deriveKey(pin, salt) {
  const m = await crypto.subtle.importKey('raw', enc.encode(pin), 'PBKDF2', false, ['deriveKey']);
  return crypto.subtle.deriveKey({ name: 'PBKDF2', salt: enc.encode(salt), iterations: 100000, hash: 'SHA-256' },
    m, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']);
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

/* ---------- Seed demo data on first load ---------- */
/* Databases created before districts existed were all in Rubavu; fill in the missing fields */
function migrateGeo() {
  const db = DB();
  if (!db) return;
  let changed = false;
  [...db.users.filter(u => u.role !== 'admin'), ...db.records].forEach(x => {
    if (!x.district) { x.province = 'West'; x.district = 'Rubavu'; changed = true; }
  });
  if (changed) S('rn_server', db);
}

async function seed() {
  if (DB()) { migrateGeo(); return; }
  const mk = async (id, name, role, login, pin, sector, cell, village) =>
    ({ id, name, role, login, hash: await sha(login + ':' + pin), province: sector ? 'West' : '', district: sector ? 'Rubavu' : '', sector, cell, village });
  const users = [
    await mk('u1', 'Aline Mukamana', 'chw', '0788000001', '1234', 'Gisenyi', 'Umuganda', 'Kabuga'),
    await mk('u2', 'Jean Bosco Habimana', 'chw', '0788000002', '2345', 'Nyamyumba', 'Burushya', 'Nyarubande'),
    await mk('u3', 'Grace Uwase', 'registrar', 'registrar', '4321', 'Gisenyi', '', ''),
    await mk('u5', 'Eric Ndayisaba', 'registrar', 'registrar2', '4322', 'Nyamyumba', '', ''),
    await mk('u4', 'System Admin', 'admin', 'admin', '9999', '', '', '')
  ];
  const names = ['Keza', 'Iradukunda', 'Mugisha', 'Uwimana', 'Ishimwe', 'Niyonsenga', 'Umutoni', 'Cyiza'];
  const demo = [
    ['Umuganda', 'Gisenyi', 'u1', 'Approved'], ['Umuganda', 'Gisenyi', 'u1', 'Synced'],
    ['Rubavu', 'Gisenyi', 'u1', 'Synced'], ['Nengo', 'Gisenyi', 'u1', 'Flagged'],
    ['Rubavu', 'Gisenyi', 'u1', 'Approved'], ['Burushya', 'Nyamyumba', 'u2', 'Synced'],
    ['Busoro', 'Nyamyumba', 'u2', 'Approved']
  ];
  const records = demo.map(([cell, sector, chw, status], i) => ({
    id: uid(), status, chw, province: 'West', district: 'Rubavu', sector, cell, village: 'Demo',
    createdAt: new Date(Date.now() - (i + 1) * 864e5).toISOString(),
    child: { given: names[i], family: 'Demo', dob: new Date(Date.now() - (i + 3) * 864e5).toISOString().slice(0, 10), pob: cell, gender: i % 2 ? 'F' : 'M' },
    mother: { given: 'Mama ' + names[i], family: 'Demo', nid: '1' + rnd(15), phone: '0788' + rnd(6) },
    father: {}, w1: { given: 'Witness', family: 'Demo', nid: '1' + rnd(15), address: cell }, w2: {}, photo: '',
    tracking: status === 'Approved' ? 'RN-2026-' + rnd(6) : '',
    flag: status === 'Flagged' ? 'Mother National ID does not match the record. Please re-check.' : ''
  }));
  const db = { users, records, sms: [], log: [] };
  logS(db, 'Demo data seeded');
  S('rn_server', db);
}
