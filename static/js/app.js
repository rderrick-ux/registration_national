/* ============================================================
   APP: top bar, sign in / sign up, language, render loop
   ============================================================ */
const icon = s => `<svg viewBox="0 0 24 24" width="${s}" height="${s}" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>`;
const DEMOS = [
  ['CHW', 'Gisenyi', '0788000001', '1234'],
  ['CHW', 'Nyamyumba', '0788000002', '2345'],
  ['Registrar', 'Gisenyi', 'registrar', '4321'],
  ['Administrator', 'All sectors', 'admin', '9999']
];

/* ---------- Top bar ---------- */
function renderBar() {
  G('bar').innerHTML = `<span class="brand"><span class="logo">${icon(18)}</span>${t('app')}</span><span class="sp"></span>
    <button class="pill ${net() ? 'on' : 'off'}" onclick="toggleNet()" title="${t('netTip')}">${net() ? t('online') : t('offline')}</button>
    <div class="lang" role="group" aria-label="${t('language')}">
      <button class="${lang === 'en' ? 'on' : ''}" onclick="setLang('en')">EN</button>
      <button class="${lang === 'rw' ? 'on' : ''}" onclick="setLang('rw')">RW</button></div>
    ${ME ? `<button class="ghost light" onclick="logout()">${t('logout')}</button>` : ''}`;
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

/* ---------- Landing, sign in, sign up ---------- */
const setAuth = a => { AUTH = a; render(); };

function authHTML() {
  const hero = `<section class="hero"><div class="logo big">${icon(30)}</div><h1>${t('hero1')}</h1><p>${t('hero2')}</p></section>`;

  if (AUTH === 'up') return hero + `<div class="card phone"><h2>${t('signup')}</h2>
    <label for="su_n">${t('name')}</label><input id="su_n" autocomplete="name">
    <label for="su_l">${t('phone')}</label><input id="su_l" inputmode="tel" maxlength="10" placeholder="07XXXXXXXX" oninput="this.value=this.value.replace(/\\D/g,'')">
    <label for="su_p">${t('pin')} (4)</label><input id="su_p" type="password" inputmode="numeric" maxlength="4">
    ${geoFields('geo_su').join('')}
    <label for="su_v">${t('village')}</label><input id="su_v">
    <div class="err" id="se"></div>
    <button class="full" onclick="doSignUp()">${t('create')}</button>
    <div class="row between"><span class="muted">${t('haveacc')}</span><button class="text" onclick="setAuth('in')">${t('signin')}</button></div>
    <button class="text" onclick="setAuth('')">${t('back2')}</button></div>`;

  if (AUTH === 'in') return hero + `<div class="card phone"><h2>${t('signin')}</h2>
    <label for="li">${t('user')}</label><input id="li" autocomplete="off">
    <label for="lp">${t('pin')}</label><input id="lp" type="password" inputmode="numeric" maxlength="4" onkeydown="if(event.key==='Enter')doLogin()">
    <div class="err" id="le"></div>
    <button class="full" onclick="doLogin()">${t('signin')}</button>
    <div class="row between"><span class="muted">${t('noacc')}</span><button class="text" onclick="setAuth('up')">${t('signup')}</button></div>
    <button class="text" onclick="setAuth('')">${t('back2')}</button></div>
    <div class="card phone"><b>${t('demo')}</b><div class="demos">${DEMOS.map(d =>
      `<button class="demo" onclick="quick('${d[2]}','${d[3]}')"><b>${d[0]}</b><span>${d[1]}</span></button>`).join('')}</div>
      <p class="muted">${t('demoNote')}</p><button class="text" onclick="resetDemo()">${t('reset')}</button></div>`;

  return hero + `<div class="card phone stack">
    <button class="cta" onclick="setAuth('in')">${t('signin')}</button>
    <button class="ghost full" onclick="setAuth('up')">${t('signup')}</button></div>`;
}

function quick(login, pin) {
  G('li').value = login;
  G('lp').value = pin;
  doLogin();
}
async function doLogin() {
  const id = G('li').value.trim(), pin = G('lp').value;
  const u = J('rn_cred', []).find(x => x.login === id);
  if (!u || u.hash !== await sha(id + ':' + pin)) {
    G('le').textContent = t('wrong') + (net() ? '' : t('wrongOff'));
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
/* Self sign-up creates CHW accounts only; registrar and admin accounts come from the admin console */
async function doSignUp() {
  const v = id => G(id).value.trim(), name = v('su_n'), login = v('su_l'), pin = G('su_p').value;
  const err = m => { G('se').textContent = m; };
  if (!name) return err(t('req') + ': ' + t('name'));
  if (!phOK(login)) return err(t('phbad'));
  if (!/^\d{4}$/.test(pin)) return err(t('pin4'));
  if (!net()) return err(t('needNet'));
  const db = DB();
  if (db.users.some(u => u.login === login)) return err(t('exists'));
  db.users.push({ id: uid(), name, role: 'chw', login, hash: await sha(login + ':' + pin),
    ...geoVal('geo_su'), village: v('su_v') });
  logS(db, 'Self sign-up: ' + login);
  S('rn_server', db);
  refreshCache();
  AUTH = 'in';
  await render();
  quick(login, pin);
}
function logout() {
  ME = KEY = W = MODAL = null;
  AUTH = '';
  render();
}
function resetDemo() {
  if (apiOK) xhr('POST', '/api/reset', '{}');
  Object.keys(LS).filter(k => k.startsWith('rn_') && k !== 'rn_lang').forEach(k => LS.removeItem(k));
  location.reload();
}

/* ---------- Render loop ---------- */
async function render() {
  renderBar();
  G('foot').textContent = t('footer');
  const app = G('app');
  if (!ME) { app.innerHTML = authHTML(); return; }
  if (ME.role === 'chw') {
    const h = await chwHTML();
    if (ME) app.innerHTML = h; else render();
    return;
  }
  app.innerHTML = !net()
    ? `<div class="card phone"><h3>${t('offline')}</h3><p>${t('offlinePortal')}</p></div>`
    : ME.role === 'registrar' ? regHTML() : admHTML();
}

/* ---------- Startup ---------- */
document.documentElement.lang = lang;
setInterval(() => { if (ME && ME.role === 'chw') sync(); }, 4000);
seed()
  .then(() => { refreshCache(); render(); })
  .catch(e => {
    G('app').innerHTML = `<div class="card phone"><h3>Startup error</h3><p>${esc(e.message)}</p>
      <p class="muted">If you opened this through an IP address, use http://localhost:8000 or HTTPS (the encryption APIs need a secure context).</p></div>`;
  });
