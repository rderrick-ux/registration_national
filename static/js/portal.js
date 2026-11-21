/* ============================================================
   PORTAL: sector registrar review + system admin console
   ============================================================ */
const go = tab => { TAB = tab; MODAL = null; render(); };
const closeModal = () => { MODAL = null; render(); };
const tabsHTML = list => `<div class="tabs">${list.map(([k, l]) =>
  `<button class="${TAB === k ? 'on' : ''}" onclick="go('${k}')">${l}</button>`).join('')}</div>`;

/* ---------- Dashboard language card (shown on every role's home screen) ---------- */
const dashCard = () => `<div class="card dash">
  <div class="muted">${t('dash')}</div><label style="margin-top:6px">${t('language')}</label>
  <div class="seg">
    <button class="${lang === 'en' ? 'on' : ''}" onclick="setLang('en')">English</button>
    <button class="${lang === 'rw' ? 'on' : ''}" onclick="setLang('rw')">Kinyarwanda</button>
  </div></div>`;

/* ---------- Registrar: record detail dialog ---------- */
function detailSection(title, x = {}) {
  const en = Object.entries(x).filter(e => e[1]);
  const body = en.length
    ? `<dl>${en.map(e => `<dt>${t(e[0])}</dt><dd>${esc(e[0] === 'gender' ? t(e[1]) : e[1])}</dd>`).join('')}</dl>`
    : '<div class="muted">-</div>';
  return `<div class="sec"><h4>${title}</h4>${body}</div>`;
}
function detailHTML(r) {
  const act = r.status === 'Synced'
    ? `<label>${t('comment')}</label><textarea id="fc" rows="2"></textarea>
       <div class="row"><button onclick="decide('${r.id}',true)">${t('approve')}</button>
       <button class="bad" onclick="decide('${r.id}',false)">${t('returnchw')}</button></div>`
    : (r.flag ? `<div class="err">${esc(r.flag)}</div>` : '') + (r.tracking ? `<p>${t('tracking')}: <b>${esc(r.tracking)}</b></p>` : '');
  return `<div class="modal" onclick="if(event.target===this)closeModal()"><div class="card">
    <div class="row between"><h3>${t('record')}</h3><span class="badge ${r.status}">${t(r.status)}</span></div>
    ${detailSection(t('child'), r.child)}${detailSection(t('mother'), r.mother)}${detailSection(t('father'), r.father)}
    ${detailSection(t('witness1'), r.w1)}${detailSection(t('witness2'), r.w2)}
    ${r.photo ? `<img class="thumb" src="${r.photo}" alt="ID photo">` : ''}${act}
    <button class="ghost" onclick="closeModal()">${t('close')}</button></div></div>`;
}

/* ---------- Registrar: approve / return a record ---------- */
function decide(id, ok) {
  const db = DB(), r = db.records.find(x => x.id === id);
  if (ok) {
    r.status = 'Approved';
    r.flag = '';
    r.tracking = 'RN-' + new Date().getFullYear() + '-' + rnd(6);
    db.sms.unshift({ at: new Date().toISOString(), to: r.mother.phone,
      text: `Registration National: birth record for ${r.child.given} ${r.child.family} approved. Tracking code ${r.tracking}.` });
    logS(db, `Approved ${r.tracking} by ${ME.login}; SMS queued to ${r.mother.phone}`);
  } else {
    const c = G('fc').value.trim();
    if (!c) return toast(t('needComment'));
    r.status = 'Flagged';
    r.flag = c;
    logS(db, `Returned record ${r.id.slice(0, 8)} by ${ME.login}`);
  }
  S('rn_server', db);
  MODAL = null;
  render();
  toast(ok ? t('okApproved') : t('okReturned'));
}

/* ---------- Registrar: review list ---------- */
function reviewTable(db) {
  let rs = db.records.filter(r => sameSector(r, ME) && ['Synced', 'Approved', 'Flagged'].includes(r.status));
  if (F.cell) rs = rs.filter(r => r.cell === F.cell);
  if (F.status) rs = rs.filter(r => r.status === F.status);
  if (F.from) rs = rs.filter(r => r.createdAt.slice(0, 10) >= F.from);
  rs.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  const cells = geoList(geoCells(ME.province, ME.district, ME.sector), F.cell);
  const sts = ['Synced', 'Approved', 'Flagged'].map(s => `<option value="${s}" ${F.status === s ? 'selected' : ''}>${t(s)}</option>`).join('');
  const rows = rs.map(r => `<tr><td>${esc(r.child.given)} ${esc(r.child.family)}</td>
    <td>${esc(r.mother.given)} ${esc(r.mother.family)}</td><td>${esc(r.cell)} / ${esc(r.village)}</td>
    <td>${r.createdAt.slice(0, 10)}</td><td><span class="badge ${r.status}">${t(r.status)}</span></td>
    <td><button class="ghost" onclick="MODAL='${r.id}';render()">${t('open')}</button></td></tr>`).join('');
  return `<div class="card filters">
      <div><label>${t('cell')}</label><select onchange="F.cell=this.value;render()"><option value="">${t('all')}</option>${cells}</select></div>
      <div><label>${t('status')}</label><select onchange="F.status=this.value;render()"><option value="">${t('all')}</option>${sts}</select></div>
      <div><label>${t('from')}</label><input type="date" value="${F.from}" onchange="F.from=this.value;render()"></div>
    </div>
    <div class="card scroll"><table><tr><th>${t('child')}</th><th>${t('mother')}</th><th>${t('cell')} / ${t('village')}</th>
      <th>${t('submitted')}</th><th>${t('status')}</th><th></th></tr>
      ${rows || `<tr><td colspan="6" class="muted">${t('none2')}</td></tr>`}</table></div>`;
}

function regHTML() {
  const db = DB();
  const all = db.records.filter(r => sameSector(r, ME)), n = k => all.filter(r => r.status === k).length;
  const m = MODAL && db.records.find(r => r.id === MODAL);
  const body = TAB === 'cov' ? covHTML(ME) : reviewTable(db);
  return `<div class="greet"><div><div class="muted">${t('regrole')}</div><h2>${esc(ME.name)}</h2></div>
      <span class="chip">${esc(ME.district)} / ${esc(ME.sector)}</span></div>
    ${dashCard()}
    ${tiles([[n('Synced'), t('await'), 'warn'], [n('Approved'), t('Approved'), 'ok'], [n('Flagged'), t('returned'), 'bad'], [all.length, t('total')]])}
    ${tabsHTML([['rev', t('rev')], ['cov', t('cov')]])}${body}${m ? detailHTML(m) : ''}`;
}

/* ---------- Coverage analytics by cell ----------
   scope = a registrar's { province, district, sector } (every cell in the sector is listed, even with no records),
   or null for the admin (only cells that have records are listed). */
function covHTML(scope) {
  const db = DB(), map = new Map();
  const row = (d, s, c) => {
    const k = [d, s, c].join('|');
    if (!map.has(k)) map.set(k, { d, s, c, tot: 0, ap: 0, pend: 0, fl: 0 });
    return map.get(k);
  };
  if (scope) geoCells(scope.province, scope.district, scope.sector).forEach(c => row(scope.district, scope.sector, c));
  db.records.filter(r => !scope || sameSector(r, scope)).forEach(r => {
    const x = row(r.district || '-', r.sector, r.cell);
    x.tot++;
    if (r.status === 'Approved') x.ap++;
    if (r.status === 'Synced') x.pend++;
    if (r.status === 'Flagged') x.fl++;
  });
  const rows = [...map.values()].sort((a, b) => a.d.localeCompare(b.d) || a.s.localeCompare(b.s) || a.c.localeCompare(b.c));
  const T = rows.reduce((a, r) => ({ tot: a.tot + r.tot, ap: a.ap + r.ap }), { tot: 0, ap: 0 });
  const trs = rows.map(r => {
    const p = r.tot ? Math.round(r.ap / r.tot * 100) : 0;
    return `<tr><td>${esc(r.d)}</td><td>${esc(r.s)}</td><td>${esc(r.c)}</td><td>${r.tot}</td><td>${r.ap}</td><td>${r.pend}</td><td>${r.fl}</td>
      <td><div class="meter"><i style="width:${p}%"></i></div>${p}%</td></tr>`;
  }).join('');
  return `<div class="card scroll"><b>${t('covTitle').replace('{a}', T.ap).replace('{t}', T.tot)}</b>
    <table><tr><th>${t('district')}</th><th>${t('sector')}</th><th>${t('cell')}</th><th>${t('submitted')}</th><th>${t('Approved')}</th>
    <th>${t('pending')}</th><th>${t('returned')}</th><th>${t('approvedRate')}</th></tr>${trs}</table></div>`;
}

/* ---------- Admin console ---------- */
function usersTable(db) {
  const rows = db.users.map(u => {
    const isChw = u.role === 'chw';
    const geo = geoFields('geo_' + u.id, u, { cell: isChw, labels: false }).map(h => `<td>${h}</td>`).join('') + (isChw ? '' : '<td>-</td>');
    const editable = u.role === 'admin' ? '<td colspan="6"></td>' : `${geo}
      <td>${isChw ? `<input id="uv_${u.id}" value="${esc(u.village)}">` : '-'}</td>
      <td><button class="ghost" onclick="updUser('${u.id}')">${t('save')}</button>
        ${u.id !== ME.id ? `<button class="ghost" onclick="delUser('${u.id}')">${t('remove')}</button>` : ''}</td>`;
    return `<tr><td>${esc(u.name)}</td><td>${u.role}</td><td>${esc(u.login)}</td>${editable}</tr>`;
  }).join('');
  return `<div class="card scroll"><table><tr><th>${t('name')}</th><th>${t('role')}</th><th>${t('login')}</th>
    <th>${t('province')}</th><th>${t('district')}</th><th>${t('sector')}</th><th>${t('cell')}</th><th>${t('village')}</th><th></th></tr>${rows}</table></div>
  <div class="card"><b>${t('createAcct')}</b><div class="filters">
    <div><label>${t('name')}</label><input id="nu_n"></div>
    <div><label>${t('role')}</label><select id="nu_r"><option value="chw">${t('roleChw')}</option><option value="registrar">${t('regrole')}</option></select></div>
    <div><label>${t('phoneUser')}</label><input id="nu_l"></div>
    <div><label>${t('pinLabel')}</label><input id="nu_p" maxlength="4" inputmode="numeric"></div>
    ${geoFields('geo_nu').map(h => `<div>${h}</div>`).join('')}
    <div><label>${t('villageChw')}</label><input id="nu_v"></div></div>
    <div class="hint">${t('cellNote')}</div>
    <button onclick="addUser()">${t('createAcct')}</button></div>`;
}
function smsTable(db) {
  const rows = db.sms.map(s => `<tr><td>${s.at.slice(0, 16).replace('T', ' ')}</td><td>${esc(s.to)}</td><td>${esc(s.text)}</td></tr>`).join('');
  return `<div class="card scroll"><table><tr><th>${t('time')}</th><th>${t('to')}</th><th>${t('msg')}</th></tr>
    ${rows || `<tr><td colspan="3" class="muted">${t('noSms')}</td></tr>`}</table></div>`;
}
const logTable = db => `<div class="card scroll"><table>${db.log.map(l =>
  `<tr><td>${l.at.slice(0, 19).replace('T', ' ')}</td><td>${esc(l.m)}</td></tr>`).join('')}</table></div>`;

function admHTML() {
  const db = DB();
  const body = { cov: () => covHTML(null), sms: () => smsTable(db), log: () => logTable(db) }[TAB] || (() => usersTable(db));
  return `<div class="greet"><div><div class="muted">${t('adminrole')}</div><h2>${esc(ME.name)}</h2></div></div>
    ${dashCard()}
    ${tiles([[db.users.length, t('accounts')], [db.records.length, t('records')],
      [db.records.filter(r => r.status === 'Approved').length, t('Approved'), 'ok'], [db.sms.length, t('smsSent')]])}
    ${tabsHTML([['usr', t('users')], ['cov', t('cov')], ['sms', t('smslog')], ['log', t('syslog')]])}${body()}`;
}

async function addUser() {
  const db = DB(), v = id => G(id).value.trim(), login = v('nu_l'), pin = v('nu_p'), g = geoVal('geo_nu');
  if (!v('nu_n') || !login || !/^\d{4}$/.test(pin)) return toast(t('needFields'));
  if (db.users.some(u => u.login === login)) return toast(t('loginUsed'));
  db.users.push({ id: uid(), name: v('nu_n'), role: v('nu_r'), login, hash: await sha(login + ':' + pin),
    ...g, cell: v('nu_r') === 'chw' ? g.cell : '', village: v('nu_v') });
  logS(db, 'Account created: ' + login);
  S('rn_server', db);
  refreshCache();
  render();
  toast(t('acctCreated'));
}
function updUser(id) {
  const db = DB(), u = db.users.find(x => x.id === id);
  const g = geoVal('geo_' + id);
  Object.assign(u, { province: g.province, district: g.district, sector: g.sector });
  if (u.role === 'chw') {
    u.cell = g.cell;
    u.village = G('uv_' + id).value.trim();
  }
  logS(db, `Jurisdiction updated for ${u.login}: ${u.district}/${u.sector}/${u.cell}/${u.village}`);
  S('rn_server', db);
  refreshCache();
  toast(t('savedOk'));
}
function delUser(id) {
  const db = DB();
  db.users = db.users.filter(u => u.id !== id);
  S('rn_server', db);
  refreshCache();
  render();
}
