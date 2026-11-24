/* Sector Registrar portal + System Admin console (FR 1.2, FR 4, FR 5). All labels go through t() so they follow the language switch. */
let F = { cell: '', status: '', from: '' }, MODAL = null;
/* Jurisdiction pickers: District > Sector > Cell cascade, because sector names repeat across districts */
const opts = (list, sel, blank) => (blank ? `<option value="">${esc(blank)}</option>` : '') + list.map(x => `<option ${x === sel ? 'selected' : ''}>${esc(x)}</option>`).join('');
const selD = (pre, d) => `<select id="${pre}_d" onchange="geoChg('${pre}','d')">${opts(districtsOf(), d, t('pickdistrict'))}</select>`;
const selS = (pre, d, s) => `<select id="${pre}_s" onchange="geoChg('${pre}','s')">${opts(sectorsOf(d), s, t('picksector'))}</select>`;
const selC = (pre, d, s, c) => `<select id="${pre}_c">${opts(cellsOf(d, s), c, t('pickcell'))}</select>`;
function geoChg(pre, lvl) {
  const d = G(pre + '_d').value;
  if (lvl === 'd') G(pre + '_s').innerHTML = opts(sectorsOf(d), '', t('picksector'));
  const c = G(pre + '_c');
  if (c) c.innerHTML = opts(cellsOf(d, G(pre + '_s').value), '', t('pickcell'));
}
/* A record belongs to a sector when district and sector both match (older records without a district match on sector alone) */
const inSector = (r, d, s) => r.sector === s && (!d || !r.district || r.district === d);
const place = x => [x.district, x.sector, x.cell].filter(Boolean).join(' / ');
const go = tab => {
  TAB = tab;
  MODAL = null;
  render();
};
const tabsHTML = list => `<div class="tabs">${list.map(([k, l]) => `<button class="${TAB === k ? 'on' : ''}" onclick="go('${k}')">${t(l)}</button>`).join('')}</div>`;
const th = keys => keys.map(k => `<th>${t(k)}</th>`).join('');
const day = iso => iso.slice(0, 10);
const person = x => `${esc(x.given)} ${esc(x.family)}`;

function detailHTML(r) {
  const part = (title, x = {}) => {
    const en = Object.entries(x).filter(e => e[1]);
    const rows = en.map(e => `<dt>${t(e[0])}</dt><dd>${esc(e[0] === 'gender' ? t(e[1]) : e[1])}</dd>`).join('');
    return `<div class="sec"><h4>${title}</h4>${en.length ? `<dl>${rows}</dl>` : '<div class="muted">-</div>'}</div>`;
  };
  const act = r.status === 'Synced'
    ? `<label>${t('commentreq')}</label><textarea id="fc" rows="2"></textarea>
       <div class="row"><button onclick="decide('${r.id}',true)">${t('approve')}</button><button class="bad" onclick="decide('${r.id}',false)">${t('returnchw')}</button></div>`
    : (r.flag ? `<div class="err">${esc(r.flag)}</div>` : '') + (r.tracking ? `<p>${t('tracking')}: <b>${esc(r.tracking)}</b></p>` : '');
  return `<div class="modal" onclick="if(event.target===this){MODAL=null;render()}"><div class="card">
    <div class="row between"><h3>${t('birthrec')}</h3><span class="badge ${r.status}">${t(r.status)}</span></div>
    ${part(t('child'), r.child)}${part(t('mother'), r.mother)}${part(t('father'), r.father)}${part(t('witness1'), r.w1)}${part(t('witness2'), r.w2)}
    ${r.photo ? `<img class="thumb" src="${r.photo}" alt="ID">` : ''}${act}
    <button class="ghost" onclick="MODAL=null;render()">${t('close')}</button></div></div>`;
}

/* Dashboard: headline numbers, 7-day submissions, status mix, busiest cells, recent records */
function dashHTML(sc) {
  const db = DB();
  const rs = db.records.filter(r => !sc || inSector(r, sc.d, sc.s));
  const n = k => rs.filter(r => r.status === k).length;
  const total = rs.length, ap = n('Approved'), rate = total ? Math.round(ap / total * 100) : 0;
  const head = [[total, t('recsub')], [n('Synced'), t('awaiting'), 'warn'], [ap, t('Approved'), 'ok'], [n('Flagged'), t('returnedchw'), 'bad'], [rate + '%', t('approvalrate')]];
  if (!sc) head.push([db.users.length, t('accounts')], [db.sms.length, t('smssent')]);
  const mix = [['Synced', t('awaiting')], ['Approved', t('Approved')], ['Flagged', t('retshort')]];
  const cells = {};
  rs.forEach(r => {
    const k = place(r);
    (cells[k] = cells[k] || { t: 0, a: 0 }).t++;
    if (r.status === 'Approved') cells[k].a++;
  });
  const top = Object.entries(cells).sort((a, b) => b[1].t - a[1].t).slice(0, 5);
  const recent = rs.slice().sort((a, b) => b.createdAt.localeCompare(a.createdAt)).slice(0, 5);
  const start = !sc && db.users.length <= 1
    ? `<div class="card start"><h4>${t('startTitle')}</h4><ol><li>${t('start1')}</li><li>${t('start2')}</li><li>${t('start3')}</li></ol></div>` : '';
  const topRows = top.map(c => `<div class="lrow"><span>${esc(c[0])}</span><div class="meter wide"><i style="width:${c[1].a / c[1].t * 100}%"></i></div><b>${c[1].a}/${c[1].t}</b></div>`).join('');
  const recentRows = recent.map(r => `<tr><td>${person(r.child)}</td><td>${esc(place(r))}</td><td>${day(r.createdAt)}</td><td><span class="badge ${r.status}">${t(r.status)}</span></td></tr>`).join('');
  return `${start}${tiles(head)}
  <div class="grid2">
    <div class="card"><h4>${t('last7')}</h4>${weekChart(rs)}</div>
    <div class="card"><h4>${t('recstatus')}</h4>
      <div class="stack">${mix.map(m => `<i class="${m[0]}" style="width:${total ? n(m[0]) / total * 100 : 0}%"></i>`).join('')}</div>
      <div class="legend">${mix.map(m => `<span class="lg"><i class="${m[0]}"></i>${m[1]}: ${n(m[0])}</span>`).join('')}</div>
      <h4 style="margin-top:18px">${t('busiest')}</h4>${topRows || `<p class="muted">${t('norecyet')}</p>`}
    </div>
  </div>
  <div class="card scroll"><h4>${t('recent')}</h4><table>${recentRows || `<tr><td class="muted">${t('nothingsub')}</td></tr>`}</table></div>`;
}

/* FR 4.1 / 4.2: review, approve or return records */
function regHTML() {
  const db = DB();
  let rs = db.records.filter(r => inSector(r, ME.district, ME.sector) && ['Synced', 'Approved', 'Flagged'].includes(r.status));
  if (F.cell) rs = rs.filter(r => r.cell === F.cell);
  if (F.status) rs = rs.filter(r => r.status === F.status);
  if (F.from) rs = rs.filter(r => day(r.createdAt) >= F.from);
  rs.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  const tabs = tabsHTML([['dash', 'dashboard'], ['rev', 'reviewrec'], ['cov', 'coverage']]);
  let body;
  if (TAB === 'dash') body = dashHTML({ d: ME.district, s: ME.sector });
  else if (TAB === 'cov') body = covHTML({ d: ME.district, s: ME.sector });
  else {
    const cellSel = opts(cellsOf(ME.district, ME.sector), F.cell);
    const statusSel = ['Synced', 'Approved', 'Flagged'].map(s => `<option value="${s}" ${F.status === s ? 'selected' : ''}>${t(s)}</option>`).join('');
    const rows = rs.map(r => `<tr><td>${person(r.child)}</td><td>${person(r.mother)}</td><td>${esc(r.cell)} / ${esc(r.village)}</td><td>${day(r.createdAt)}</td>
      <td><span class="badge ${r.status}">${t(r.status)}</span></td><td><button class="ghost" onclick="MODAL='${r.id}';render()">${t('open')}</button></td></tr>`).join('');
    body = `<div class="card filters">
      <div><label>${t('cell')}</label><select onchange="F.cell=this.value;render()"><option value="">${t('allopt')}</option>${cellSel}</select></div>
      <div><label>${t('status')}</label><select onchange="F.status=this.value;render()"><option value="">${t('allopt')}</option>${statusSel}</select></div>
      <div><label>${t('subfrom')}</label><input type="date" value="${F.from}" onchange="F.from=this.value;render()"></div></div>
      <div class="card scroll"><table><tr>${th(['child', 'mother', 'cellvillage', 'submitted', 'status'])}<th></th></tr>
      ${rows || `<tr><td colspan="6" class="muted">${t('nomatch')}</td></tr>`}</table></div>`;
  }
  const m = MODAL && db.records.find(r => r.id === MODAL);
  return `<div class="greet"><div><div class="muted">${t('role_registrar')}</div><h2>${esc(ME.name)}</h2></div><span class="chip">${ME.district ? esc(ME.district) + ' / ' : ''}${t('sector')} ${esc(ME.sector)}</span></div>${tabs}${body}${m ? detailHTML(m) : ''}`;
}
function decide(id, ok) {
  const db = DB(), r = db.records.find(x => x.id === id);
  if (ok) {
    r.status = 'Approved';
    r.flag = '';
    r.tracking = 'RN-' + new Date().getFullYear() + '-' + rnd(6);
    /* FR 5.1: SMS with the tracking code (written to the SMS log in this prototype) */
    db.sms.unshift({ at: new Date().toISOString(), to: r.mother.phone, text: t('smstext').replace('{name}', `${r.child.given} ${r.child.family}`).replace('{code}', r.tracking) });
    logS(db, `Approved ${r.tracking} by ${ME.login}; SMS queued to ${r.mother.phone}`);
  } else {
    const c = G('fc').value.trim();
    if (!c) return toast(t('needcomment'));
    r.status = 'Flagged';
    r.flag = c;
    logS(db, `Returned record ${r.id.slice(0, 8)} by ${ME.login}`);
  }
  S('rn_server', db);
  MODAL = null;
  render();
  toast(ok ? t('approvedsms') : t('returned'));
}

/* FR 5.2: coverage analytics by cell. A registrar sees the cells of their own sector; the administrator sees all
   30 districts and drills into one district at a time (2,000+ cells would be an unusable single table). */
let CF = { p: '', d: '' };
const tally = rs => ({ tot: rs.length, ap: rs.filter(r => r.status === 'Approved').length, pend: rs.filter(r => r.status === 'Synced').length, fl: rs.filter(r => r.status === 'Flagged').length });
const rateCell = x => {
  const p = x.tot ? Math.round(x.ap / x.tot * 100) : 0;
  return `<div class="meter"><i style="width:${p}%"></i></div>${p}%`;
};
const numCells = x => `<td>${x.tot}</td><td>${x.ap}</td><td>${x.pend}</td><td>${x.fl}</td><td>${rateCell(x)}</td>`;
const sumT = rows => rows.reduce((a, r) => ({ tot: a.tot + r.tot, ap: a.ap + r.ap }), { tot: 0, ap: 0 });
function covHTML(sc) {
  const db = DB();
  if (sc) {
    /* Registrar: every cell of the sector, including cells with no records yet */
    const rows = cellsOf(sc.d, sc.s).map(c => ({ c, ...tally(db.records.filter(r => inSector(r, sc.d, sc.s) && r.cell === c)) }));
    return covTable(rows.map(r => `<tr><td>${esc(sc.s)}</td><td>${esc(r.c)}</td>${numCells(r)}</tr>`), sumT(rows), ['sector', 'cell']);
  }
  /* Administrator */
  const byD = {}, byC = {};
  db.records.forEach(r => {
    (byD[r.district || ''] = byD[r.district || ''] || []).push(r);
    const k = [r.district, r.sector, r.cell].join('|');
    (byC[k] = byC[k] || []).push(r);
  });
  const provSel = `<select onchange="CF.p=this.value;CF.d='';render()"><option value="">${t('allopt')}</option>${provinces().map(p => `<option value="${p}" ${CF.p === p ? 'selected' : ''}>${esc(PROV_LABEL[lang][p])}</option>`).join('')}</select>`;
  const distSel = `<select onchange="CF.d=this.value;render()"><option value="">${t('covall')}</option>${opts(districtsOf(CF.p), CF.d)}</select>`;
  const g = GEO_TOTALS;
  const filters = `<div class="card filters"><div><label>${t('province')}</label>${provSel}</div><div><label>${t('district')}</label>${distSel}</div>
    <div class="muted" style="align-self:end">${t('geoinfo').replace('{d}', g.districts).replace('{s}', g.sectors).replace('{c}', g.cells.toLocaleString())}</div></div>`;
  if (!CF.d) {
    const rows = districtsOf(CF.p).map(d => {
      const secs = sectorsOf(d);
      return { d, ns: secs.length, nc: secs.reduce((n, x) => n + cellsOf(d, x).length, 0), ...tally(byD[d] || []) };
    });
    const tr = rows.map(r => `<tr><td>${esc(PROV_LABEL[lang][PROVINCE_OF[r.d]])}</td><td><b>${esc(r.d)}</b></td><td>${r.ns}</td><td>${r.nc}</td>${numCells(r)}
      <td><button class="ghost" onclick="CF.d='${esc(r.d)}';render()">${t('open')}</button></td></tr>`).join('');
    const T = sumT(rows);
    return `${filters}<div class="card scroll"><b>${t('covnational').replace('{a}', T.ap).replace('{t}', T.tot)}</b>
      <p class="muted">${t('covdrill')}</p><table><tr>${th(['province', 'district', 'sectors', 'cells', 'submitted', 'Approved', 'pending', 'retshort', 'apprate'])}<th></th></tr>${tr}</table></div>`;
  }
  const rows = [];
  sectorsOf(CF.d).forEach(sec => cellsOf(CF.d, sec).forEach(c => rows.push({ sec, c, ...tally(byC[[CF.d, sec, c].join('|')] || []) })));
  const out = covTable(rows.map(r => `<tr><td>${esc(r.sec)}</td><td>${esc(r.c)}</td>${numCells(r)}</tr>`), sumT(rows), ['sector', 'cell']);
  return `${filters}<p><button class="ghost" onclick="CF.d='';render()">&larr; ${t('covback')}</button></p>
    <h3>${esc(CF.d)} <span class="muted">${t('covscope').replace('{c}', rows.length)}</span></h3>${out}`;
}
function covTable(trs, T, lead) {
  return `<div class="card scroll"><b>${t('covtitle').replace('{a}', T.ap).replace('{t}', T.tot)}</b>
    <table><tr>${th([...lead, 'submitted', 'Approved', 'pending', 'retshort', 'apprate'])}</tr>${trs.join('')}</table></div>`;
}

/* FR 1.2: administrator console (accounts, jurisdictions, coverage, SMS log) */
function admHTML() {
  const db = DB();
  const tabs = tabsHTML([['dash', 'dashboard'], ['usr', 'users'], ['cov', 'coverage'], ['sms', 'smslog']]);
  let body;
  if (TAB === 'dash') body = dashHTML(null);
  else if (TAB === 'cov') body = covHTML(null);
  else if (TAB === 'sms') {
    const rows = db.sms.map(s => `<tr><td>${s.at.slice(0, 16).replace('T', ' ')}</td><td>${esc(s.to)}</td><td>${esc(s.text)}</td></tr>`).join('');
    body = `<div class="card scroll"><table><tr>${th(['time', 'to', 'message'])}</tr>${rows || `<tr><td colspan="3" class="muted">${t('nosms')}</td></tr>`}</table></div>`;
  } else {
    const rows = db.users.map(u => {
      const pre = 'u_' + u.id;
      const jur = u.role === 'admin' ? '<td colspan="5"></td>' : `<td>${selD(pre, u.district)}</td><td>${selS(pre, u.district, u.sector)}</td>
        <td>${u.role === 'chw' ? selC(pre, u.district, u.sector, u.cell) : '-'}</td>
        <td>${u.role === 'chw' ? `<input id="uv_${u.id}" value="${esc(u.village)}">` : '-'}</td>
        <td><button class="ghost" onclick="updUser('${u.id}')">${t('save')}</button> ${u.id !== ME.id ? `<button class="ghost" onclick="delUser('${u.id}')">${t('remove')}</button>` : ''}</td>`;
      return `<tr><td>${esc(u.name)}</td><td>${t('role_' + u.role)}</td><td>${esc(u.login)}</td>${jur}</tr>`;
    }).join('');
    body = `<div class="card scroll"><table><tr>${th(['name', 'role', 'loginlbl', 'district', 'sector', 'cell', 'village'])}<th></th></tr>${rows}</table></div>
    <div class="card"><b>${t('createacct')}</b><div class="filters">
      <div><label>${t('fullname')}</label><input id="nu_n"></div>
      <div><label>${t('role')}</label><select id="nu_r"><option value="chw">${t('role_chw')}</option><option value="registrar">${t('role_registrar')}</option><option value="admin">${t('role_admin')}</option></select></div>
      <div><label>${t('phoneuser')}</label><input id="nu_l"></div>
      <div><label>${t('pin4')}</label><input id="nu_p" maxlength="4" inputmode="numeric"></div>
      <div><label>${t('district')}</label>${selD('nu', '')}</div>
      <div><label>${t('sector')}</label>${selS('nu', '', '')}</div>
      <div><label>${t('cellchw')}</label>${selC('nu', '', '', '')}</div>
      <div><label>${t('villagechw')}</label><input id="nu_v"></div></div>
      <button onclick="addUser()">${t('createacct')}</button></div>`;
  }
  return `<div class="greet"><div><div class="muted">${t('role_admin')}</div><h2>${esc(ME.name)}</h2></div></div>${tabs}${body}`;
}
async function addUser() {
  const db = DB(), v = id => G(id).value.trim(), login = v('nu_l'), pin = v('nu_p');
  if (!v('nu_n') || !login || !/^\d{4}$/.test(pin)) return toast(t('userbad'));
  if (db.users.some(u => u.login === login)) return toast(t('dup'));
  const role = v('nu_r'), geo = role === 'admin' ? { district: '', sector: '', cell: '', village: '' } : { district: G('nu_d').value, sector: G('nu_s').value, cell: role === 'chw' ? G('nu_c').value : '', village: role === 'chw' ? v('nu_v') : '' };
  if (role !== 'admin' && (!geo.district || !geo.sector || (role === 'chw' && !geo.cell))) return toast(t('needgeo'));
  db.users.push({ id: uid(), name: v('nu_n'), role, login, hash: await sha(login + ':' + pin), ...geo });
  logS(db, 'Account created: ' + login);
  S('rn_server', db);
  refreshCache();
  render();
  toast(t('created'));
}
function updUser(id) {
  const db = DB(), u = db.users.find(x => x.id === id);
  const pre = 'u_' + id, d = G(pre + '_d').value, sec = G(pre + '_s').value, cell = u.role === 'chw' ? G(pre + '_c').value : '';
  if (!d || !sec || (u.role === 'chw' && !cell)) return toast(t('needgeo'));
  u.district = d;
  u.sector = sec;
  if (u.role === 'chw') {
    u.cell = cell;
    u.village = G('uv_' + id).value.trim();
  }
  logS(db, `Jurisdiction updated for ${u.login}: ${u.district}/${u.sector}/${u.cell}/${u.village}`);
  S('rn_server', db);
  refreshCache();
  toast(t('savedok'));
}
function delUser(id) {
  const db = DB();
  db.users = db.users.filter(u => u.id !== id);
  S('rn_server', db);
  refreshCache();
  render();
}
