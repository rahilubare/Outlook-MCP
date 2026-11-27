"""HTML for the landing page, login page and dashboard. All email text is inserted with textContent (XSS-safe)."""

BASE_CSS = r"""
*{box-sizing:border-box}
:root{--bg:#f6f7fb;--card:#fff;--ink:#14161a;--mute:#667085;--line:#e4e7ec;--brand:#4f46e5;--brandink:#fff;--soft:#eef0ff;--bl:36%;--shadow:0 1px 2px rgba(16,24,40,.06),0 8px 24px rgba(16,24,40,.06)}
@media(prefers-color-scheme:dark){:root{--bg:#0d0f14;--card:#161a22;--ink:#eef1f6;--mute:#98a2b3;--line:#262c38;--brand:#8b93ff;--brandink:#0d0f14;--soft:#1d2140;--bl:74%;--shadow:none}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
.brand{display:flex;gap:10px;align-items:center;font-weight:700;font-size:17px;letter-spacing:-.01em}
.logo{width:32px;height:32px;border-radius:9px;background:linear-gradient(135deg,#6366f1,#8b5cf6);display:grid;place-items:center;color:#fff;font-size:16px}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:9px 16px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--ink);font:inherit;font-weight:600;cursor:pointer;transition:.15s}
.btn:hover{border-color:var(--brand)}
.btn.primary{background:var(--brand);border-color:var(--brand);color:var(--brandink)}
.btn.primary:hover{filter:brightness(1.08)}
.btn.big{padding:13px 22px;font-size:16px;border-radius:12px}
.btn:disabled{opacity:.6;cursor:wait}
.btn:focus-visible,input:focus-visible,select:focus-visible,button:focus-visible{outline:3px solid color-mix(in srgb,var(--brand) 40%,transparent);outline-offset:2px}
input,select{font:inherit;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:10px 13px}
"""

LOGIN = r"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sign in - MailRouter</title>
<style>/*BASE*/
.auth{min-height:100vh;display:grid;place-items:center;padding:20px}
.box{width:100%;max-width:400px;background:var(--card);border:1px solid var(--line);border-radius:18px;padding:32px;box-shadow:var(--shadow)}
.box h1{font-size:24px;margin:22px 0 4px;letter-spacing:-.02em}.sub{color:var(--mute);margin:0 0 6px}
label{display:block;font-weight:600;font-size:14px;margin:16px 0 6px}
.field{position:relative}input{width:100%}
.eye{position:absolute;right:6px;top:50%;transform:translateY(-50%);border:0;background:none;color:var(--mute);cursor:pointer;padding:6px 8px;font:inherit;font-size:13px}
.err{display:none;margin-top:16px;padding:10px 12px;border-radius:10px;background:#fef3f2;color:#b42318;font-size:14px}
.err.on{display:block}
@media(prefers-color-scheme:dark){.err{background:#3a1512;color:#fda29b}}
.box .btn{width:100%;margin-top:20px}.back{display:block;text-align:center;margin-top:16px;color:var(--mute);font-size:14px}
</style>
<main class="auth"><form class="box" id="f">
<a class="brand" href="/"><span class="logo">&#9993;</span>MailRouter</a>
<h1>Welcome back</h1><p class="sub">Sign in to see your department inboxes.</p>
<label for="u">Username</label><input id="u" autocomplete="username" required autofocus>
<label for="p">Password</label><div class="field"><input id="p" type="password" autocomplete="current-password" required><button type="button" class="eye" id="eye" aria-label="Show password">Show</button></div>
<div class="err" id="err" role="alert"></div>
<button class="btn primary big" id="go" type="submit">Sign in</button>
</form></main>
<script>
const f=document.getElementById('f'),err=document.getElementById('err'),b=document.getElementById('go'),u=document.getElementById('u'),p=document.getElementById('p');
document.getElementById('eye').onclick=e=>{const s=p.type==='password';p.type=s?'text':'password';e.target.textContent=s?'Hide':'Show'};
f.onsubmit=async e=>{e.preventDefault();err.classList.remove('on');b.disabled=true;b.textContent='Signing in...';
 try{const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value})});
  if(r.ok){location.href='/app';return}
  const j=await r.json().catch(()=>({}));err.textContent=j.detail||'Sign-in failed.';err.classList.add('on');p.select()}
 catch(x){err.textContent='Cannot reach the server.';err.classList.add('on')}
 b.disabled=false;b.textContent='Sign in'};
</script></html>""".replace("/*BASE*/", BASE_CSS)

APP = r"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dashboard - MailRouter</title>
<style>/*BASE*/
body{height:100vh;display:flex;flex-direction:column;overflow:hidden}
header{display:flex;gap:14px;align-items:center;padding:12px 20px;background:var(--card);border-bottom:1px solid var(--line)}
.search{max-width:380px;flex:1;margin-left:auto}.search input{width:100%}
.layout{flex:1;display:flex;min-height:0}
aside{width:260px;border-right:1px solid var(--line);background:var(--card);padding:14px 10px;overflow:auto}
aside button{display:flex;width:100%;justify-content:space-between;align-items:center;gap:8px;padding:9px 12px;border:0;border-radius:9px;background:none;color:var(--ink);font:inherit;cursor:pointer;text-align:left}
aside button:hover{background:var(--bg)}aside button.on{background:var(--soft);color:var(--brand);font-weight:600}
aside .n{font-size:12px;color:var(--mute);background:var(--bg);border-radius:99px;padding:1px 8px}
aside .z{opacity:.55}
main{flex:1;overflow:auto;padding:20px}
.top{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:14px}.top h2{margin:0;font-size:20px}.top span{color:var(--mute);font-size:14px}
.row{display:grid;grid-template-columns:40px 1fr auto;gap:2px 14px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:13px 15px;margin-bottom:8px}
.av{grid-row:span 3;width:40px;height:40px;border-radius:50%;display:grid;place-items:center;font-weight:700;color:hsl(var(--h) 60% var(--bl));background:hsl(var(--h) 70% 50%/.16)}
.sub1{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.meta{grid-column:2/-1;color:var(--mute);font-size:13px}
.prev{grid-column:2/-1;color:var(--mute);font-size:13.5px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.row select{padding:5px 8px;font-size:13px;max-width:190px}
.empty{text-align:center;color:var(--mute);padding:60px 0}
.more{display:flex;margin:14px auto}
.toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--ink);color:var(--bg);padding:10px 16px;border-radius:10px;opacity:0;transition:.2s;pointer-events:none}.toast.on{opacity:1}
@media(max-width:760px){.layout{flex-direction:column}aside{width:auto;display:flex;gap:6px;border-right:0;border-bottom:1px solid var(--line);overflow-x:auto;flex:none}aside button{width:auto;white-space:nowrap}.search{max-width:none}.brand span:not(.logo){display:none}}
</style>
<header><a class="brand" href="/"><span class="logo">&#9993;</span><span>MailRouter</span></a>
<div class="search"><input id="q" type="search" placeholder="Search subject, sender or text" aria-label="Search emails"></div>
<button class="btn" id="out">Sign out</button></header>
<div class="layout"><aside id="nav" aria-label="Departments"></aside>
<main><div class="top"><h2 id="title">All emails</h2><span id="count"></span></div><div id="list"></div></main></div>
<div class="toast" id="toast" role="status"></div>
<script>
const PAGE=30;let S={dept:null,q:'',off:0,depts:[],counts:{},total:0};
const $=s=>document.querySelector(s);
const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e};
async function api(p,o){const r=await fetch(p,o);if(r.status===401){location.href='/login';throw new Error('signed out')}if(!r.ok)throw new Error((await r.text()).slice(0,200));return r.json()}
const where=e=>{const f=(e.folder||'').replace(/^[\W_]+/,''),l=f.split('/').pop().replace(/^[\W_]+/,'');return f&&l!==e.department?' \u00b7 in '+f:''};
const hue=s=>{let h=0;for(const c of s)h=(h*31+c.charCodeAt(0))%360;return h};
const ago=d=>{const s=(Date.now()-new Date(d))/1e3;if(isNaN(s))return'';if(s<60)return'just now';if(s<3600)return Math.floor(s/60)+'m ago';if(s<86400)return Math.floor(s/3600)+'h ago';if(s<604800)return Math.floor(s/86400)+'d ago';return new Date(d).toLocaleDateString()};
function toast(m){const t=$('#toast');t.textContent=m;t.classList.add('on');clearTimeout(toast.t);toast.t=setTimeout(()=>t.classList.remove('on'),2200)}
function nav(){const a=$('#nav');a.replaceChildren();
 const add=(label,n,d)=>{const b=el('button',S.dept===d?'on':(n?'':'z'));b.append(el('span','',label),el('span','n',n));b.onclick=()=>{S.dept=d;reload()};a.append(b)};
 add('All emails',S.total,null);S.depts.forEach(d=>add(d,S.counts[d]||0,d))}
async function stats(){const s=await api('/api/stats');S.counts=s.counts;S.total=s.total;S.depts=s.departments;nav()}
async function reload(){S.off=0;nav();await page(true)}
async function page(reset){
 const u=`/api/emails?limit=${PAGE}&offset=${S.off}`+(S.dept?'&department='+encodeURIComponent(S.dept):'')+(S.q?'&q='+encodeURIComponent(S.q):'');
 const {emails}=await api(u),l=$('#list');
 if(reset)l.replaceChildren();
 l.querySelector('.more')?.remove();
 $('#title').textContent=S.dept||'All emails';$('#count').textContent=(S.dept?S.counts[S.dept]||0:S.total)+' emails';
 if(reset&&!emails.length){l.append(el('div','empty',S.q?'No emails match your search.':'No emails in this department yet.'));return}
 emails.forEach(e=>l.append(row(e)));
 if(emails.length===PAGE){const m=el('button','btn more','Load more');m.onclick=()=>{S.off+=PAGE;page(false)};l.append(m)}}
function row(e){const r=el('div','row'),who=e.sender_name||e.sender||'?';
 const av=el('div','av',(who.match(/[A-Za-z0-9]/)||['?'])[0].toUpperCase());av.style.setProperty('--h',hue(e.sender||who));
 const sel=el('select');sel.setAttribute('aria-label','Route to department');
 S.depts.forEach(d=>{const o=el('option','',d);o.value=d;o.selected=d===e.department;sel.append(o)});
 sel.onchange=async()=>{try{await api('/api/route',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email_id:e.id,department:sel.value})});toast('Moved to '+sel.value);await stats();await reload()}catch(x){toast('Could not move the email')}};
 r.append(av,el('div','sub1',e.subject||'(no subject)'),sel,el('div','meta',`${who} \u00b7 ${ago(e.received)}${e.routed_by==='manual'?' \u00b7 manual':''}${where(e)}`),el('div','prev',e.preview));return r}
let t;$('#q').oninput=()=>{clearTimeout(t);t=setTimeout(()=>{S.q=$('#q').value.trim();reload()},300)};
$('#out').onclick=async()=>{await fetch('/api/logout',{method:'POST'});location.href='/'};
stats().then(()=>page(true));
setInterval(async()=>{if(document.activeElement.tagName==='SELECT'||S.off>0)return;await stats();await page(true)},30000);
</script></html>""".replace("/*BASE*/", BASE_CSS)
