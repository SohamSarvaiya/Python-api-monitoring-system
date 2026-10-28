DASHBOARD_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>API Monitoring System</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wdth,wght@12..96,75..100,400..800&display=swap" rel="stylesheet">
<style>
:root{--bg:#eef2f4;--surface:#fff;--ink:#13242b;--muted:#5e7279;--line:#d9e1e5;--up:#1f9d6b;--down:#d9404a;--warn:#b7791f;--accent:#2457d6;--downbg:#fdf0f0;color-scheme:light}
@media(prefers-color-scheme:dark){:root{--bg:#0c171c;--surface:#12222a;--ink:#e6eef0;--muted:#8aa0a7;--line:#22363e;--up:#3dd598;--down:#ff6b6b;--warn:#f2b35c;--accent:#7fa2ff;--downbg:#2a1a1f;color-scheme:dark}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 "Bricolage Grotesque",system-ui,sans-serif;font-variant-numeric:tabular-nums}
main{max-width:1120px;margin:0 auto;padding:22px 22px 60px}
a{color:var(--accent)}
button,select,input{font:inherit;color:var(--ink)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.top{display:flex;justify-content:space-between;align-items:center;gap:12px}
.brand{font-weight:700;font-size:16px;letter-spacing:-.01em}.brand span{color:var(--muted);font-weight:400;margin-left:10px}
.btn{border:1px solid var(--line);background:var(--surface);border-radius:8px;padding:6px 12px;cursor:pointer}
.btn:hover{border-color:var(--muted)}.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
.btn.quiet{border:0;background:none;padding:4px 8px;color:var(--muted)}.btn.quiet:hover{color:var(--ink);text-decoration:underline}
.btn.quiet.danger:hover{color:var(--down)}
.hero{padding:44px 0 30px}
h1{margin:0;font-size:clamp(34px,6vw,60px);line-height:1.02;font-weight:700;font-stretch:80%;letter-spacing:-.025em;display:flex;align-items:center;gap:18px}
.dot{flex:none;width:16px;height:16px;border-radius:50%;background:var(--up);box-shadow:0 0 0 0 var(--up);animation:pulse 2.4s ease-out infinite}
.dot.down{background:var(--down);box-shadow:0 0 0 0 var(--down)}.dot.none{background:var(--muted);animation:none}
@keyframes pulse{70%{box-shadow:0 0 0 12px transparent}100%{box-shadow:0 0 0 0 transparent}}
@media(prefers-reduced-motion:reduce){.dot{animation:none}}
.facts{display:flex;flex-wrap:wrap;gap:6px 28px;margin-top:14px;color:var(--muted)}.facts b{color:var(--ink);font-weight:600}
.list{background:var(--surface);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.row{display:grid;grid-template-columns:minmax(170px,1.2fr) minmax(220px,2fr) 76px 84px auto;gap:6px 18px;align-items:center;padding:14px 18px;border-top:1px solid var(--line)}
.row:first-child{border-top:0}.row.down{background:var(--downbg);box-shadow:inset 3px 0 var(--down)}
.name{display:flex;gap:11px;align-items:center;min-width:0}.name i{flex:none;width:9px;height:9px;border-radius:50%;background:var(--up)}
.row.down .name i{background:var(--down)}.row.unknown .name i{background:var(--muted)}
.name b{display:block;font-weight:600}.name small{display:block;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.strip{display:flex;gap:2px;height:34px;align-items:flex-end}.strip u{flex:1;min-width:2px;border-radius:2px;background:var(--up);opacity:.85}
.strip u.f{background:var(--down);opacity:1}.strip u.e{background:var(--line);opacity:.7;height:18%}
.stat{text-align:right;line-height:1.2}.stat b{display:block;font-size:16px;font-weight:600}.stat small{color:var(--muted)}
.stat.warn b{color:var(--warn)}.acts{display:flex;justify-content:flex-end}
.empty{padding:36px;text-align:center;color:var(--muted)}
.cols{display:grid;grid-template-columns:1fr 1.5fr;gap:44px;margin-top:44px}
h2{font-size:18px;font-weight:700;margin:0 0 12px;letter-spacing:-.01em}
section{border-top:2px solid var(--ink);padding-top:14px}
.al{display:grid;grid-template-columns:14px 1fr;gap:0 10px;padding:9px 0;border-bottom:1px solid var(--line)}
.al i{width:9px;height:9px;border-radius:50%;margin-top:7px;background:var(--up)}.al.DOWN i{background:var(--down)}
.al small{color:var(--muted)}.al p{margin:0}
.ctl{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:12px;color:var(--muted)}
select,input{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:6px 10px}
.note{border-left:3px solid var(--warn);padding:2px 0 2px 12px;margin:12px 0;color:var(--muted)}
.cause{padding:12px 0;border-top:1px solid var(--line)}.cause h3{margin:0 0 4px;font-size:15px;font-weight:600}
.pill{display:inline-block;margin-left:8px;padding:0 8px;border-radius:99px;font-size:12px;font-weight:600;border:1px solid var(--line);color:var(--muted)}
.pill.high{color:var(--down);border-color:var(--down)}.pill.medium{color:var(--warn);border-color:var(--warn)}
ul,ol{margin:4px 0 0;padding-left:20px;color:var(--muted)}h4{margin:14px 0 2px;font-size:14px}
dialog{border:1px solid var(--line);border-radius:14px;background:var(--surface);color:var(--ink);padding:22px;width:min(420px,92vw)}
dialog::backdrop{background:rgba(5,12,16,.55)}dialog label{display:block;margin:12px 0 4px;font-weight:600}dialog input,dialog select{width:100%}
dialog .bar{display:flex;gap:8px;justify-content:flex-end;margin-top:18px;align-items:center}.err{color:var(--down);margin-right:auto}
@media(max-width:820px){.row{grid-template-columns:1fr 1fr;grid-template-areas:"n n""s s""u l""a a"}.row>.name{grid-area:n}.row>.strip{grid-area:s}
.row>.stat:nth-of-type(1){grid-area:u;text-align:left}.row>.stat:nth-of-type(2){grid-area:l}.row>.acts{grid-area:a;justify-content:flex-start}.cols{grid-template-columns:1fr;gap:30px}}
</style></head><body><main>
<header class="top"><div class="brand">API Monitor<span>checks every few seconds, alerts when it matters</span></div>
<div><a href="/docs" class="btn quiet">API docs</a> <button class="btn primary" id="open">Add monitor</button></div></header>

<div class="hero"><h1><i class="dot none" id="dot"></i><span id="head">Loading…</span></h1><div class="facts" id="facts"></div></div>
<div class="list" id="list"></div>

<div class="cols">
<section><h2>Recent alerts</h2><div id="alerts"></div></section>
<section><h2>Why did it fail?</h2>
<div class="ctl"><label for="prov">AI provider</label><select id="prov"><option value="">Auto</option><option value="anthropic">Claude</option><option value="openai">ChatGPT</option><option value="gemini">Gemini</option></select>
<select id="lang" aria-label="Language"><option value="en">English</option><option value="hi">हिन्दी</option></select><span id="provinfo"></span></div>
<div id="ai" class="muted" style="color:var(--muted)">Pick “Analyze” on a service that has failed at least 3 times. The AI suggests possible causes, never a proven root cause.</div></section>
</div>

<dialog id="dlg"><form id="form"><h2>Add monitor</h2>
<label for="n">Name</label><input id="n" required maxlength="100" placeholder="Payments API">
<label for="u">URL</label><input id="u" required type="url" placeholder="https://api.example.com/health">
<label for="i">Check every</label><select id="i"><option value="15">15 seconds</option><option value="30">30 seconds</option><option value="60" selected>1 minute</option><option value="300">5 minutes</option></select>
<div class="bar"><span class="err" id="err"></span><button type="button" class="btn" id="cancel">Cancel</button><button class="btn primary">Add monitor</button></div></form></dialog>
</main>
<script>
const $=s=>document.querySelector(s);
const el=(t,a={},...k)=>{const e=document.createElement(t);for(const[n,v]of Object.entries(a))n==='class'?e.className=v:n==='text'?e.textContent=v:e.setAttribute(n,v);k.flat().forEach(x=>x!=null&&e.append(x));return e};
async function api(p,o){const r=await fetch(p,o);if(!r.ok){let d=r.statusText;try{const j=await r.json();d=typeof j.detail==='string'?j.detail:d}catch{}throw new Error(d)}return r.status===204?null:r.json()}
const ago=iso=>{const s=Math.max(0,Math.round((Date.now()-new Date(iso))/1000));return s<60?s+' s ago':s<3600?Math.round(s/60)+' min ago':Math.round(s/3600)+' h ago'};
const btn=(t,fn,c='')=>{const b=el('button',{class:'btn quiet '+c,text:t});b.onclick=()=>fn(b);return b};

function strip(checks){
  const c=[...checks].reverse(),max=Math.max(1,...c.filter(x=>x.ok).map(x=>x.response_ms||0)),n=60,box=el('div',{class:'strip',role:'img','aria-label':'Last '+c.length+' checks'});
  for(let i=0;i<n-c.length;i++)box.append(el('u',{class:'e'}));
  c.forEach(x=>box.append(el('u',{class:x.ok?'':'f',style:'height:'+(x.ok?Math.max(22,Math.round(x.response_ms/max*100)):100)+'%',title:ago(x.checked_at)+': '+(x.ok?Math.round(x.response_ms)+' ms':(x.error||'failed'))})));
  return box}

async function load(){
  const [reps,alerts]=await Promise.all([api('/reports/uptime?hours=24'),api('/alerts?limit=8')]);
  const hist=await Promise.all(reps.map(r=>api('/monitors/'+r.monitor_id+'/checks?limit=60')));
  const down=reps.filter(r=>r.state==='down'),n=reps.length;
  const tot=reps.reduce((a,r)=>a+r.total_checks,0),ok=reps.reduce((a,r)=>a+r.successful_checks,0);
  const newest=hist.flat().map(c=>c.checked_at).sort().pop();
  $('#head').textContent=!n?'Add your first API to start monitoring.':down.length?down.length+' of '+n+(n>1?' services':' service')+(down.length>1?' are':' is')+' down.':(n>1?'All '+n+' services are up.':'Your service is up.');
  $('#dot').className='dot '+(!n?'none':down.length?'down':'');
  document.title=(down.length?'('+down.length+' down) ':'')+'API Monitoring System';
  const f=$('#facts');f.replaceChildren();
  if(n){f.append(el('span',{},'24-hour uptime ',el('b',{text:tot?(ok/tot*100).toFixed(2)+'%':'–'})));
    if(newest)f.append(el('span',{},'Last check ',el('b',{text:ago(newest)})));
    if(down.length)f.append(el('span',{},'Needs attention: ',el('b',{text:down.map(d=>d.name).join(', ')})))}
  const L=$('#list');L.replaceChildren();
  if(!n)L.append(el('div',{class:'empty',text:'No monitors yet. Add an API URL and the first check runs within seconds.'}));
  reps.forEach((r,i)=>{
    const avg=r.latency_ms.avg,slow=avg>2000;
    L.append(el('div',{class:'row '+r.state},
      el('div',{class:'name'},el('i'),el('div',{style:'min-width:0'},el('b',{text:r.name}),el('small',{text:r.url}))),
      strip(hist[i]),
      el('div',{class:'stat'},el('b',{text:r.uptime_percent==null?'–':r.uptime_percent.toFixed(1)+'%'}),el('small',{text:'uptime'})),
      el('div',{class:'stat'+(slow?' warn':'')},el('b',{text:avg==null?'–':Math.round(avg)+' ms'}),el('small',{text:slow?'slow':'average'})),
      el('div',{class:'acts'},btn('Check',async b=>{b.textContent='…';await api('/monitors/'+r.monitor_id+'/check',{method:'POST'});load()}),
        btn('Analyze',()=>analyze(r.monitor_id,r.name)),
        btn('Delete',async()=>{if(confirm('Delete '+r.name+' and its history?')){await api('/monitors/'+r.monitor_id,{method:'DELETE'});load()}},'danger'))))});
  const A=$('#alerts');A.replaceChildren();
  alerts.forEach(a=>A.append(el('div',{class:'al '+a.kind},el('i'),el('div',{},el('p',{text:a.message.replace(/^[^\w]+/,'')}),el('small',{text:ago(a.created_at)})))));
  if(!alerts.length)A.append(el('p',{text:'No alerts yet. You will see one when a service fails 3 checks in a row, and another when it recovers.',style:'color:var(--muted)'}))}

function list(tag,items){return items&&items.length?el(tag,{},items.map(x=>el('li',{text:String(x)}))):null}
async function analyze(id,name){
  const box=$('#ai');box.replaceChildren(el('p',{text:'Analyzing '+name+'…'}));
  try{const q=new URLSearchParams({language:$('#lang').value});if($('#prov').value)q.set('provider',$('#prov').value);
    const d=await api('/monitors/'+id+'/analyze?'+q,{method:'POST'});box.replaceChildren();
    if(d.status==='insufficient_data'){box.append(el('p',{class:'note',text:d.message}));return}
    const a=d.analysis;box.append(el('p',{style:'color:var(--muted);margin:0',text:name+' analysed by '+d.provider+' ('+d.model+')'}));
    if(a.raw_text){box.append(el('p',{text:a.raw_text}))}else{
      box.append(el('p',{text:a.summary||''}));
      (a.possible_causes||[]).forEach(c=>box.append(el('div',{class:'cause'},el('h3',{},c.cause,el('span',{class:'pill '+c.confidence,text:c.confidence+' confidence'})),
        list('ul',c.supporting_evidence),c.needed_to_confirm&&c.needed_to_confirm.length?el('div',{style:'color:var(--muted);margin-top:6px'},'To confirm: ',c.needed_to_confirm.join('; ')):null)));
      if(a.troubleshooting_steps&&a.troubleshooting_steps.length)box.append(el('h4',{text:'What to try'}),list('ol',a.troubleshooting_steps));
      if(a.data_limitations&&a.data_limitations.length)box.append(el('h4',{text:'What the data cannot tell us'}),list('ul',a.data_limitations))}
    box.append(el('p',{class:'note',text:d.disclaimer}))
  }catch(e){box.replaceChildren(el('p',{class:'note',text:e.message}))}}

$('#open').onclick=()=>{$('#err').textContent='';$('#dlg').showModal();$('#n').focus()};
$('#cancel').onclick=()=>$('#dlg').close();
$('#form').onsubmit=async e=>{e.preventDefault();
  try{await api('/monitors',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:$('#n').value,url:$('#u').value,interval_seconds:+$('#i').value})});
    $('#form').reset();$('#dlg').close();load()}catch(x){$('#err').textContent=x.message}};
api('/ai/providers').then(d=>{const k=Object.entries(d.providers).filter(([,v])=>v.configured).map(([k])=>k);$('#provinfo').textContent=k.length?'Key found: '+k.join(', '):'No AI key yet. Monitoring works without one.'}).catch(()=>{});
load();setInterval(load,10000);
</script></body></html>"""
