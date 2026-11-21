/* ============================================================
   CHW: offline intake wizard, encrypted local queue, auto-sync
   ============================================================ */
const STEPS = [
  { k: 'child',  f: ['given', 'family', 'dob', 'pob', 'gender'], r: 1 },
  { k: 'mother', f: ['given', 'family', 'nid', 'phone'],         r: 1 },
  { k: 'father', f: ['given', 'family', 'nid', 'phone'],         r: 0 },
  { k: 'w1',     f: ['given', 'family', 'nid', 'address'],       r: 1 },
  { k: 'w2',     f: ['given', 'family', 'nid', 'address'],       r: 0 }
];
const TITLES = { child: 'child', mother: 'mother', father: 'father', w1: 'witness1', w2: 'witness2' };
const HINTS = { pob: 'hintPob', phone: 'hintPhone' };

/* ---------- Encrypted local storage (per user) ---------- */
const lk = () => 'rn_local_' + ME.id;
const loadLocal = () => unseal(KEY, LS.getItem(lk()));
const saveLocal = async a => LS.setItem(lk(), await seal(KEY, a));

/* ---------- Validation (16-digit National ID, phone and date formats) ---------- */
function validate(st, d = {}) {
  const e = {}, any = Object.values(d).some(x => x);
  st.f.forEach(f => {
    const v = (d[f] || '').trim();
    const required = st.r ? true : (any && f !== 'phone');
    if (required && !v) e[f] = t('req');
    else if (v) {
      if (f === 'nid' && !nidOK(v)) e[f] = t('nid16');
      if (f === 'phone' && !phOK(v)) e[f] = t('phbad');
      if (f === 'dob' && new Date(v) > new Date()) e[f] = t('dobfut');
    }
  });
  return e;
}
const fmtErr = d => STEPS.some(st => {
  const x = d[st.k] || {};
  return (x.nid && !nidOK(x.nid)) || (x.phone && !phOK(x.phone));
});

/* ---------- Wizard navigation ---------- */
function collect() {
  if (W.step >= 5) return;
  const st = STEPS[W.step], o = {};
  st.f.forEach(f => { const el = G('f_' + f); if (el) o[f] = el.value.trim(); });
  W.d[st.k] = o;
}
function setG(g, btn) {
  G('f_gender').value = g;
  btn.parentNode.querySelectorAll('button').forEach(b => b.classList.toggle('on', b === btn));
}
function jump(i) { W.step = i; W.err = null; render(); }
function goNew() { W = { step: 0, d: {}, id: null, err: null }; render(); }
function goRec() { W = null; render(); }
function back() { collect(); W.err = null; W.step--; render(); }
function next() {
  collect();
  const st = STEPS[W.step], e = validate(st, W.d[st.k]);
  if (Object.keys(e).length) { W.err = e; render(); return; }
  W.err = null;
  W.step++;
  render();
}

/* ---------- Wizard views ---------- */
const stepper = () => `<div class="steps">${[0, 1, 2, 3, 4, 5].map(i =>
  `<i class="${i < W.step ? 'done' : i === W.step ? 'cur' : ''}"></i>`).join('')}</div>`;

function fieldHTML(f, d, e) {
  let inp, hint = HINTS[f] ? `<div class="hint">${t(HINTS[f])}</div>` : '';
  if (f === 'gender') {
    inp = `<input type="hidden" id="f_gender" value="${esc(d.gender)}"><div class="seg">${['M', 'F'].map(g =>
      `<button type="button" class="${d.gender === g ? 'on' : ''}" onclick="setG('${g}',this)">${t(g)}</button>`).join('')}</div>`;
  } else if (f === 'nid') {
    inp = `<input id="f_nid" value="${esc(d.nid)}" inputmode="numeric" maxlength="16" oninput="this.value=this.value.replace(/\\D/g,'');G('h_nid').textContent=this.value.length+'/16 '+t('digits')">`;
    hint = `<div class="hint" id="h_nid">${(d.nid || '').length}/16 ${t('digits')}</div>`;
  } else if (f === 'phone') {
    inp = `<input id="f_phone" value="${esc(d.phone)}" inputmode="tel" maxlength="10" placeholder="07XXXXXXXX" oninput="this.value=this.value.replace(/\\D/g,'')">`;
  } else {
    const type = f === 'dob' ? `type="date" max="${new Date().toISOString().slice(0, 10)}"` : '';
    inp = `<input id="f_${f}" value="${esc(d[f])}" ${type}>`;
  }
  return `<label for="f_${f}">${t(f)}</label>${inp}${e[f] ? `<div class="err">${e[f]}</div>` : hint}`;
}

function wizHTML() {
  const s = W.step;
  if (s === 5) return reviewHTML();
  const st = STEPS[s], d = W.d[st.k] || {}, e = W.err || {};
  return `<div class="card">
      <div class="row between" style="margin:0"><span class="muted">${t('step')} ${s + 1}/6</span>
        <button class="text" onclick="goRec()">${t('cancel')}</button></div>
      ${stepper()}<h3>${t(TITLES[st.k])}</h3>${st.f.map(f => fieldHTML(f, d, e)).join('')}
    </div>
    <div class="actions">${s ? `<button class="ghost" onclick="back()">${t('back')}</button>` : ''}
      <button class="ghost" onclick="draftRec()">${t('savedraft')}</button>
      <button class="go" onclick="next()">${t('next')}</button></div>`;
}

function reviewSection(k, i) {
  const en = Object.entries(W.d[k] || {}).filter(x => x[1]);
  const body = en.length
    ? `<dl>${en.map(x => `<dt>${t(x[0])}</dt><dd>${esc(x[0] === 'gender' ? t(x[1]) : x[1])}</dd>`).join('')}</dl>`
    : '<div class="muted">-</div>';
  return `<div class="sec"><div class="row between" style="margin:0"><h4>${t(TITLES[k])}</h4>
    <button class="text" onclick="jump(${i})">${t('edit')}</button></div>${body}</div>`;
}
function reviewHTML() {
  return `<div class="card"><span class="muted">${t('step')} 6/6</span>${stepper()}<h3>${t('review')}</h3>
      ${STEPS.map((x, i) => reviewSection(x.k, i)).join('')}
      <label>${t('photo')}</label><input type="file" accept="image/*" capture="environment" onchange="pick(this)">
      ${W.d.photo ? `<img class="thumb" src="${W.d.photo}" alt="ID photo">` : ''}
    </div>
    <div class="actions"><button class="ghost" onclick="back()">${t('back')}</button>
      <button class="ghost" onclick="draftRec()">${t('savedraft')}</button>
      <button class="go" onclick="submitRec()">${t('submit')}</button></div>`;
}

/* Downscale the ID photo before storing it */
function pick(el) {
  const f = el.files[0];
  if (!f) return;
  const img = new Image();
  img.onload = () => {
    const c = document.createElement('canvas'), k = Math.min(1, 480 / Math.max(img.width, img.height));
    c.width = img.width * k;
    c.height = img.height * k;
    c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
    W.d.photo = c.toDataURL('image/jpeg', .6);
    render();
  };
  img.src = URL.createObjectURL(f);
}

/* ---------- Record actions ---------- */
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
    if (Object.keys(e).length) { W.step = i; W.err = e; toast(t('fix')); return render(); }
  }
  await saveRec('Queued');
  toast(net() ? t('sent') : t('saved'));
}
async function saveRec(status) {
  const recs = await loadLocal(), d = W.d;
  let r = recs.find(x => x.id === W.id);
  if (!r) {
    r = { id: uid(), createdAt: new Date().toISOString(), chw: ME.id, province: ME.province, district: ME.district, sector: ME.sector, cell: ME.cell, village: ME.village };
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

/* ---------- Sync: push queued records, pull registrar decisions ---------- */
async function sync(manual) {
  if (!ME || ME.role !== 'chw' || busy) return;
  if (!net()) { if (manual) toast(t('offnote')); return; }
  busy = true;
  try {
    const recs = await loadLocal(), db = DB();
    if (!ME) return;
    let pushed = 0, changed = false;
    for (const r of recs) {
      if (r.status === 'Queued') {
        if ((r.district || ME.district) !== ME.district || r.sector !== ME.sector) {   // jurisdiction check
          logS(db, '403 jurisdiction mismatch for ' + ME.login);
          changed = true;
          continue;
        }
        const i = db.records.findIndex(x => x.id === r.id), copy = { ...r, province: r.province || ME.province, district: r.district || ME.district, status: 'Synced' };
        if (i < 0) db.records.push(copy); else db.records[i] = copy;
        r.status = 'Synced';
        pushed++;
        changed = true;
      } else if (r.status === 'Synced') {
        const s = db.records.find(x => x.id === r.id);
        if (s && (s.status === 'Approved' || s.status === 'Flagged')) {
          Object.assign(r, { status: s.status, tracking: s.tracking, flag: s.flag });
          changed = true;
        }
      }
    }
    if (pushed) logS(db, `POST /sync ${pushed} record(s) from ${ME.login}: 200 OK`);
    if (changed) {
      S('rn_server', db);
      await saveLocal(recs);
      if (!W) render();
      if (pushed) toast(t('synced') + ' ' + pushed);
    }
  } finally {
    busy = false;
  }
}

/* ---------- CHW home screen ---------- */
function recCard(r) {
  const days = Math.floor((Date.now() - new Date(r.createdAt)) / 864e5);
  const warn = r.status === 'Queued' && days >= 25 ? `<div class="err">${t('queuedWarn').replace('{n}', days)}</div>` : '';
  const actions = ['Draft', 'Flagged'].includes(r.status)
    ? `<div class="row"><button class="ghost" onclick="editRec('${r.id}')">${t('edit')}</button>${
        r.status === 'Draft' ? `<button class="text" onclick="delRec('${r.id}')">${t('del')}</button>` : ''}</div>` : '';
  return `<div class="rec" data-s="${r.status}">
    <div class="row between" style="margin:0"><b>${esc(r.child.given || '-')} ${esc(r.child.family || '')}</b>
      <span class="badge ${r.status}">${t(r.status)}</span></div>
    <div class="muted">${new Date(r.createdAt).toLocaleDateString()} - ${esc(r.mother.given || '')} ${esc(r.mother.family || '')}</div>
    ${r.tracking ? `<span class="chip big">${t('tracking')}: ${esc(r.tracking)}</span>` : ''}
    ${r.flag ? `<div class="err">${esc(r.flag)}</div>` : ''}${warn}${actions}</div>`;
}

async function chwHTML() {
  const recs = await loadLocal();
  if (!ME) return '';
  const count = k => recs.filter(r => r.status === k).length, q = count('Queued');
  const banner = net() ? '' : `<div class="banner">${t('offnote')}</div>`;
  const head = `<div class="phone"><div class="greet"><div><div class="muted">${t('welcome')},</div>
    <h2>${esc(ME.name.split(' ')[0])}</h2></div>
    <span class="chip">${esc(ME.district)} / ${esc(ME.sector)} / ${esc(ME.cell)} / ${esc(ME.village)}</span></div>${banner}`;
  if (W) return head + wizHTML() + '</div>';

  const list = recs.sort((a, b) => b.createdAt.localeCompare(a.createdAt)).map(recCard).join('');
  const syncRow = q && net()
    ? `<div class="row between"><span class="muted">${t('waiting')}: ${q}</span><button class="ghost" onclick="sync(true)">${t('syncnow')}</button></div>` : '';
  return head + dashCard() +
    `<button class="cta" onclick="goNew()">+ ${t('register')}</button>` +
    tiles([[q, t('Queued'), 'warn'], [count('Synced'), t('Synced')], [count('Approved'), t('Approved'), 'ok'], [count('Flagged'), t('Flagged'), 'bad']]) +
    syncRow + (list || `<div class="empty"><h3>${t('none')}</h3><p>${t('register')}</p></div>`) + '</div>';
}
