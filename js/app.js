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
function renderBar() {
  G('bar').innerHTML = `<span class="brand">${LOGO}${t('app')}</span><span class="sp"></span>
  <button class="pill ${net() ? 'on' : 'off'}" onclick="toggleNet()" title="${t('nettip')}">${net() ? t('online') : t('offline')}</button>
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
  <p class="muted center">${t('accnote')}</p>`;
}
async function doLogin() {
  const id = G('li').value.trim(), pin = G('lp').value;
  const u = J('rn_cred', []).find(x => x.login === id);
  if (!u || u.hash !== await sha(id + ':' + pin)) {
    G('le').textContent = t('wrongcred') + (net() ? '' : t('wrongoff'));
    return;
  }
  ME = u;
  KEY = await deriveKey(pin, 'rn:' + u.id);
  W = null;
  MODAL = null;
  TAB = u.role === 'chw' ? '' : 'dash';
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

async function render() {
  renderBar();
  document.body.dataset.role = ME ? ME.role : '';
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
  else if (!net()) app.innerHTML = `<div class="card phone"><h3>${t('offtitle')}</h3><p>${t('offtext')}</p></div>`;
  else app.innerHTML = ME.role === 'registrar' ? regHTML() : admHTML();
  labelTables();
}
/* Copy each column heading onto its cells so tables can turn into labelled cards on phones (see styles.css) */
function labelTables() {
  document.querySelectorAll('#app table').forEach(tb => {
    const head = [...tb.rows].find(r => r.querySelector('th'));
    if (!head) return;
    head.classList.add('thead');
    const names = [...head.cells].map(c => c.textContent.trim());
    [...tb.rows].forEach(r => {
      if (r === head) return;
      [...r.cells].forEach((c, i) => { if (names[i] && c.colSpan === 1) c.dataset.label = names[i]; });
    });
  });
}

setInterval(() => { if (ME && ME.role === 'chw') sync(); }, 4000);
document.documentElement.lang = lang;
seed().then(() => { refreshCache(); render(); });
