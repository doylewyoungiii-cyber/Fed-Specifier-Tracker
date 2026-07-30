#!/usr/bin/env python3
"""Generate index.html - "Prospect OS": a Channel OS-style multi-view app for
CEU lunch-and-learn prospecting.

Views: Overview / Targets / Firm detail / Cadence / To-Dos / L&L Events /
Reports / Settings / Guide. Autosaves to the browser as you type; Save to
cloud pushes state to data/prospecting.json AND refreshes data/targets.csv
(so the Excel workbook rebuild stays in sync) via the GitHub Contents API.

Usage:  python scripts/build_site.py
"""
import base64
import csv
import json
import os
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "data", "targets.csv")
LOGO_PATH = os.path.join(ROOT, "assets", "XtraLight-LED-Lighting-Logo.png")
OUT_PATH = os.path.join(ROOT, "index.html")

COLS = ["state", "firm", "city", "type", "website", "strengths", "standing",
        "fit", "tier", "angle", "rep", "status", "course", "office",
        "contact", "title", "email", "outreach", "lldate", "next", "notes"]


def load():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        rows = []
        for r in reader:
            if len(r) < 2 or not r[1].strip():
                continue
            r = (r + [""] * len(COLS))[:len(COLS)]
            d = dict(zip(COLS, [v.strip() for v in r]))
            if not d["status"]:
                d["status"] = "Not Started"
            rows.append(d)
    rows.sort(key=lambda d: (d["state"], d["firm"]))
    return rows


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#15181D">
<title>XtraLight | Prospect OS</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root{--bg:#15181D;--panel:#1D2127;--panel2:#232830;--line:#2E343D;--txt:#E8EAED;
--dim:#9AA3AD;--blue:#0079C1;--blue2:#3FA9E8;--green:#5D9732;--gold:#C49F06;--red:#D64541;}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Montserrat',Arial,sans-serif;background:var(--bg);color:var(--txt);font-size:13px}
a{color:var(--blue2);text-decoration:none;font-weight:600;cursor:pointer}
.app{display:flex;min-height:100vh}
/* ---- sidebar ---- */
nav{width:212px;background:#101317;border-right:1px solid var(--line);padding:14px 0;flex-shrink:0}
.logobox{background:#fff;border-radius:10px;margin:0 14px 8px;padding:10px 12px;text-align:center}
.logobox img{width:100%;max-width:150px}
.ostag{font-size:9.5px;font-weight:800;letter-spacing:.16em;color:var(--dim);text-align:center;margin-bottom:14px}
nav .item{display:flex;justify-content:space-between;align-items:center;padding:9px 18px;
font-weight:600;color:var(--dim);cursor:pointer;border-left:3px solid transparent}
nav .item:hover{color:var(--txt)}
nav .item.on{color:#fff;border-left-color:var(--blue);background:var(--panel)}
nav .item .n{font-size:10.5px;font-weight:800;background:var(--panel2);border-radius:8px;padding:1px 7px}
nav .item .n.red{background:var(--red);color:#fff}
.me{margin:16px 18px 0;padding-top:12px;border-top:1px solid var(--line);font-size:11px;color:var(--dim)}
.me b{color:var(--txt);display:block;font-size:12px}
/* ---- main ---- */
main{flex:1;min-width:0;padding:18px 24px 60px}
.top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;margin-bottom:14px}
.top h1{font-size:19px;font-weight:900}
.top .sub{font-size:11.5px;color:var(--dim);margin-top:2px}
.top .ctl{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
button{font-family:inherit;font-weight:700;font-size:12px;border:none;border-radius:8px;
padding:8px 13px;cursor:pointer;background:var(--panel2);color:var(--txt)}
button.b{background:var(--blue);color:#fff}
button.ghost{background:transparent;border:1.5px solid var(--line)}
button.danger{background:#3A2020;color:#F2A9A7}
button:disabled{opacity:.45;cursor:default}
.sync{font-size:11px;color:var(--dim)}
.sync.ok{color:#8FCB6B}.sync.err{color:#F2A9A7}
/* ---- cards / grids ---- */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(128px,1fr));gap:10px;margin-bottom:16px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi .v{font-size:23px;font-weight:900;color:var(--blue2)}
.kpi .l{font-size:9.5px;font-weight:700;letter-spacing:.07em;color:var(--dim);text-transform:uppercase;margin-top:2px}
.kpi.warn .v{color:var(--gold)}.kpi.bad .v{color:var(--red)}.kpi.good .v{color:#8FCB6B}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:14px}
.card h3{font-size:11px;font-weight:800;letter-spacing:.12em;color:var(--blue2);margin-bottom:10px;text-transform:uppercase}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:900px){.grid2{grid-template-columns:1fr}nav{width:64px}
.logobox{margin:0 8px 8px;padding:6px}.ostag{display:none}
nav .item{padding:9px 0;justify-content:center}nav .item .t{display:none}nav .item .n{display:none}
.me{display:none}.hidemob{display:none}}
/* ---- tables ---- */
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{color:var(--dim);text-align:left;font-size:10px;letter-spacing:.08em;padding:7px 9px;
border-bottom:1px solid var(--line);text-transform:uppercase;cursor:pointer;user-select:none}
td{padding:8px 9px;border-bottom:1px solid var(--line);vertical-align:top}
tr.rw:hover{background:var(--panel2)}
.badge{display:inline-block;padding:2px 9px;border-radius:9px;font-size:10.5px;font-weight:700;white-space:nowrap}
.b-grey{background:#2C3138;color:#B7BEC6}.b-blue{background:#0E3E5C;color:#8FD0F5}
.b-gold{background:#4A3E10;color:#F0D375}.b-green{background:#2C4519;color:#B4E08C}
.b-dgreen{background:var(--green);color:#fff}.b-dim{background:#26292E;color:#7C848D}
.b-red{background:#4A1D1B;color:#F2A9A7}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}
.dg{background:#6BBF3F}.dy{background:var(--gold)}.dr{background:var(--red)}
.t1{color:var(--blue2);font-weight:800}.t2{color:var(--gold);font-weight:800}.t3{color:var(--dim);font-weight:800}
/* ---- inputs ---- */
input,select,textarea{font-family:inherit;font-size:12.5px;background:var(--panel2);
color:var(--txt);border:1.5px solid var(--line);border-radius:7px;padding:7px 9px;width:100%}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--blue)}
textarea{min-height:60px;resize:vertical}
.fld label{display:block;font-size:9.5px;font-weight:700;letter-spacing:.06em;
color:var(--dim);text-transform:uppercase;margin-bottom:3px}
.form{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px 12px}
.wide{grid-column:1/-1}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.filters input,.filters select{width:auto}
.filters input{flex:1;min-width:170px}
.x{color:var(--red);cursor:pointer;font-weight:800;padding:0 5px}
.muted{color:var(--dim)}
.bar{height:13px;border-radius:7px;background:var(--blue);min-width:2px}
.frow{display:flex;align-items:center;gap:10px;margin:5px 0}
.frow .lab{width:112px;font-size:11.5px;font-weight:600;color:var(--dim)}
.note-item{border-left:3px solid var(--blue);padding:6px 10px;margin:6px 0;background:var(--panel2);border-radius:0 7px 7px 0}
.note-item .m{font-size:10.5px;color:var(--dim)}
.chk{width:auto}
.todo-line{display:flex;gap:8px;align-items:flex-start;padding:6px 0;border-bottom:1px solid var(--line)}
.todo-line.done .t{text-decoration:line-through;color:var(--dim)}
.todo-line .due{font-size:10.5px}
.overdue{color:var(--red);font-weight:700}
.pill{font-size:10px;font-weight:700;background:var(--panel2);border-radius:8px;padding:2px 8px;color:var(--dim)}
footer{position:fixed;bottom:0;left:0;right:0;background:#0C0E11;border-top:1px solid var(--line);
padding:8px 16px;display:flex;justify-content:space-between;font-size:10.5px;color:var(--dim);z-index:5}
footer .tag{font-weight:700;color:#fff}
.help{font-size:11px;color:var(--dim);line-height:1.5;margin-top:8px}
.guide p,.guide li{font-size:12.5px;line-height:1.6;color:var(--txt)}
.guide ol,.guide ul{margin:6px 0 14px 20px}
.guide b{color:var(--blue2)}
h4.gsec{font-size:11px;font-weight:800;letter-spacing:.1em;color:var(--gold);margin:16px 0 6px;text-transform:uppercase}
</style>
<script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-auth-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore-compat.js"></script>
</head>
<body>
<div class="app">
<nav id="nav"></nav>
<main>
<div class="top">
<div><h1 id="vTitle"></h1><div class="sub" id="vSub"></div></div>
<div class="ctl">
<span class="sync" id="sync"></span>
<span class="pill" id="userChip" style="display:none"></span>
<button class="ghost" id="signBtn">Sign in</button>
<button class="ghost" id="cloudLoad">&#8595; Load GitHub</button>
<button class="b" id="cloudSave">&#8593; Publish workbook</button>
</div>
</div>
<div id="view"></div>
</main>
</div>
<footer>
<div class="tag">Working Harder. Lighting Smarter.&reg;</div>
<div>XtraLight Manufacturing, Ltd. &middot; 8812 Frey Road, Houston, TX 77034 &middot; 800-678-6960 &middot; xtralight.com</div>
</footer>

<div id="login" style="display:none;position:fixed;inset:0;background:rgba(10,12,15,.93);z-index:50;align-items:center;justify-content:center">
<div class="card" style="width:340px;max-width:92vw">
<div class="logobox"><img src="data:image/png;base64,__LOGO__" alt="XtraLight" style="width:100%;max-width:170px"></div>
<div class="ostag">PROSPECT OS</div>
<div class="fld"><label>Email</label><input id="lgE" type="email" autocomplete="username"></div>
<div class="fld" style="margin-top:8px"><label>Password</label><input id="lgP" type="password" autocomplete="current-password"></div>
<div id="lgErr" class="sync err" style="margin-top:6px"></div>
<button class="b" id="lgGo" style="width:100%;margin-top:10px">Sign in</button>
<div class="help" style="margin-top:8px">Same accounts as Channel OS (Firebase console &rarr; Authentication &rarr; Users).
Data syncs live across all signed-in devices.</div>
<div style="margin-top:8px;text-align:center"><a id="lgSkip">Use local-only on this device</a></div>
</div></div>

<div id="addm" style="display:none;position:fixed;inset:0;background:rgba(10,12,15,.93);z-index:40;align-items:flex-start;justify-content:center;overflow:auto;padding:30px 12px">
<div class="card" style="width:780px;max-width:96vw">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
<h3 style="margin:0">ADD TARGETS</h3><span class="x" id="amX" style="font-size:20px">&#215;</span></div>
<div style="display:flex;gap:8px;margin-bottom:12px">
<button class="b" id="amTab1">Single target</button>
<button class="ghost" id="amTab2">Bulk import</button></div>
<div id="amSingle">
<div class="form">
<div class="fld"><label>State (HQ) *</label><input id="aState" placeholder="FL"></div>
<div class="fld"><label>Firm *</label><input id="aFirm"></div>
<div class="fld"><label>HQ city</label><input id="aCity"></div>
<div class="fld"><label>Firm type</label><input id="aType" placeholder="MEP Engineering"></div>
<div class="fld"><label>Website</label><input id="aWeb" placeholder="firm.com"></div>
<div class="fld"><label>Tier</label><select id="aTier"><option>Tier 1</option><option selected>Tier 2</option><option>Tier 3</option></select></div>
<div class="fld"><label>CEU fit</label><select id="aFit"><option>FED</option><option>COR</option><option>FED+COR</option></select></div>
<div class="fld"><label>Rep agency</label><input id="aRep"></div>
<div class="fld wide"><label>Angle / entry notes</label><input id="aAngle"></div>
</div>
<div id="aErr" class="sync err" style="margin-top:6px"></div>
<button class="b" style="margin-top:10px" id="aGo">Add target</button>
</div>
<div id="amBulk" style="display:none">
<div class="help">Paste rows copied from Excel (tab-separated) or CSV text &mdash; or choose a .csv file.
Minimal columns in order: <b>State, Firm, City, Website, Tier, Fit</b>. A header row is detected
automatically, and full 21-column exports from this app or the repo CSV import as-is.</div>
<textarea id="bTxt" style="margin-top:8px;min-height:110px" placeholder="FL, TLC Engineering Solutions, Orlando, tlc-engineers.com, Tier 1, FED"></textarea>
<div style="display:flex;gap:10px;margin-top:8px;align-items:center;flex-wrap:wrap">
<input type="file" id="bFile" accept=".csv,.txt" style="width:auto">
<button class="b" id="bParse">Preview</button>
<label style="font-size:12px;text-transform:none"><input type="checkbox" class="chk" id="bUpd"> Update existing firms with imported values</label>
</div>
<div id="bPrev" style="margin-top:10px"></div>
</div>
</div></div>

<script>
/* ================= data ================= */
const SEED = __DATA__;
const BUILD = "__DATE__";
const STATUSES=["Not Started","Outreach Sent","In Scheduling","Scheduled","Presented","Follow-Up","Declined","Dormant"];
const SB={"Not Started":"b-grey","Outreach Sent":"b-blue","In Scheduling":"b-gold","Scheduled":"b-green",
"Presented":"b-dgreen","Follow-Up":"b-blue","Declined":"b-dim","Dormant":"b-dim"};
const EVSTATUS=["Scheduled","Completed","Needs Follow-Up","Converted to Spec Activity","Cancelled"];
const LSK="prospect_os_v1";
const fid=d=>d.state+"||"+d.firm;
const today=()=>new Date().toISOString().slice(0,10);

function seedState(){
  return {
    firms: SEED.map(d=>({...d, id:fid(d),
      notes: d.notes? [{d:today(),who:"import",what:d.notes,next:d.next||""}]:[],
      lastTouch:"", nextSched:"", champion:""})),
    todos: [], events: [],
    settings:{green:14,yellow:30,owner:"doylewyoungiii-cyber",repo:"xtralight-ceu-targets",
      branch:"main",remember:false,me:"DWY"},
    token:""
  };
}
let S;
try{S=JSON.parse(localStorage.getItem(LSK))}catch(e){}
if(!S||!S.firms){S=seedState();}
S.settings=Object.assign({green:14,yellow:30,owner:"doylewyoungiii-cyber",
  repo:"xtralight-ceu-targets",branch:"main",remember:false,me:"DWY"},S.settings||{});
S.imports=S.imports||[]; S.firms.forEach(f=>{f.notes=f.notes||[];});
let TOKEN=S.token||"";

function save(){
  const store={...S, token:S.settings.remember?TOKEN:""};
  try{localStorage.setItem(LSK,JSON.stringify(store))}catch(e){}
  if(!USER)stamp("Saved locally \u00B7 "+new Date().toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"}));
  renderNavCounts(); schedulePush();
}
function stamp(t,cls){const el=document.getElementById("sync");el.textContent=t;el.className="sync "+(cls||"");}
function esc(s){return String(s??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}

/* ================= computed ================= */
const firm=id=>S.firms.find(f=>f.id===id);
function daysSince(d){if(!d)return null;return Math.floor((new Date(today())-new Date(d))/864e5);}
function flag(f){const ds=daysSince(f.lastTouch);
  if(ds===null)return "r"; if(ds<=S.settings.green)return "g"; if(ds<=S.settings.yellow)return "y"; return "r";}
function overdueTodos(){return S.todos.filter(t=>!t.done&&t.due&&t.due<today());}
function openTodos(){return S.todos.filter(t=>!t.done);}
function busAdd(dstr,n){let d=new Date(dstr);let a=0;while(a<n){d.setDate(d.getDate()+1);
  if(d.getDay()!==0&&d.getDay()!==6)a++;}return d.toISOString().slice(0,10);}
function fuDue(ev){return ev.date?busAdd(ev.date,5):"";}
function needsAttention(){
  return S.firms.filter(f=>!["Declined","Dormant"].includes(f.status))
   .map(f=>{const why=[];
     if(flag(f)==="r")why.push(f.lastTouch?daysSince(f.lastTouch)+"d since touch":"never touched");
     const od=S.todos.filter(t=>!t.done&&t.firmId===f.id&&t.due&&t.due<today());
     if(od.length)why.push(od.length+" overdue to-do");
     return {f,why};})
   .filter(x=>x.why.length&&x.f.tier==="Tier 1").slice(0,50);}
function kcount(s){return S.firms.filter(f=>f.status===s).length;}

/* ================= nav / routing ================= */
const NAV=[["overview","Overview"],["targets","Targets"],["cadence","Cadence"],
["todos","To-Do List"],["events","L&L Events"],["reports","Reports"],
["settings","Settings"],["guide","User Guide"]];
function renderNav(){
  const cur=(location.hash.split("/")[1]||"overview");
  document.getElementById("nav").innerHTML =
   `<div class="logobox"><img src="data:image/png;base64,__LOGO__" alt="XtraLight"></div>
    <div class="ostag">PROSPECT OS &middot; CEU H2 2026</div>`+
   NAV.map(([k,l])=>{
     let n="";
     if(k==="cadence"){const r=S.firms.filter(f=>flag(f)==="r"&&!["Declined","Dormant"].includes(f.status)).length;
       n=`<span class="n ${r?"red":""}">${r}</span>`;}
     if(k==="todos"){const o=overdueTodos().length;n=`<span class="n ${o?"red":""}">${openTodos().length}</span>`;}
     if(k==="targets")n=`<span class="n">${S.firms.length}</span>`;
     return `<div class="item ${cur===k?"on":""}" onclick="location.hash='#/${k}'">
       <span class="t">${l}</span>${n}</div>`;}).join("")+
   `<div class="me"><b>Doyle W. Young III</b>Director, NA Channel Sales<br>
    <span class="muted">build ${BUILD}</span></div>`;
}
function renderNavCounts(){renderNav();}
window.addEventListener("hashchange",render);

function head(t,s){document.getElementById("vTitle").textContent=t;
  document.getElementById("vSub").innerHTML=s||"";}

/* ================= views ================= */
const V={};

V.overview=function(){
  head("Overview","CEU lunch & learn prospecting \u00B7 "+S.firms.length+" targets");
  const t=S.firms.length, ns=kcount("Not Started"), sch=kcount("Scheduled"), pr=kcount("Presented");
  const act=kcount("Outreach Sent")+kcount("In Scheduling");
  const rate=(t-ns)>0?Math.round(100*(sch+pr)/(t-ns)):0;
  const od=overdueTodos().length;
  const red=S.firms.filter(f=>flag(f)==="r"&&f.tier==="Tier 1"&&!["Declined","Dormant"].includes(f.status)).length;
  const kp=[[t,"Targets"],[S.firms.filter(f=>f.tier==="Tier 1").length,"Tier 1"],
   [act,"Active outreach"],[sch,"Scheduled"],[pr,"Presented"],[rate+"%","Booked rate"],
   [od,"Overdue to-dos",od?"bad":"good"],[red,"Tier 1 cold",red?"warn":"good"]];
  const mx=Math.max(...STATUSES.map(kcount),1);
  const upcoming=S.events.filter(e=>e.status==="Scheduled").sort((a,b)=>a.date<b.date?-1:1).slice(0,6);
  const fus=S.events.filter(e=>e.status==="Needs Follow-Up"||
    (e.status==="Completed"&&e.fu!=="Done"&&fuDue(e)<=today()));
  document.getElementById("view").innerHTML =
  `<div class="kpis">${kp.map(k=>`<div class="kpi ${k[2]||""}"><div class="v">${k[0]}</div><div class="l">${k[1]}</div></div>`).join("")}</div>
  <div class="grid2">
  <div class="card"><h3>Pipeline by status</h3>
   ${STATUSES.map(s=>{const n=kcount(s);return `<div class="frow"><div class="lab">${s}</div>
    <div class="bar" style="width:${Math.max(2,Math.round(230*n/mx))}px"></div>
    <div class="muted" style="font-weight:700">${n}</div></div>`;}).join("")}</div>
  <div class="card"><h3>Needs attention \u2014 Tier 1</h3>
   ${needsAttention().slice(0,8).map(x=>`<div class="frow">
    <span class="dot dr"></span><a onclick="go('${esc(x.f.id)}')">${esc(x.f.firm)}</a>
    <span class="muted">\u00B7 ${esc(x.why.join(" \u00B7 "))}</span></div>`).join("")||'<div class="muted">All clear.</div>'}
   <div style="margin-top:8px"><a onclick="location.hash='#/cadence'">Open Cadence \u2192</a></div></div>
  <div class="card"><h3>Upcoming sessions</h3>
   ${upcoming.map(e=>{const f=firm(e.firmId);return `<div class="frow"><span class="pill">${esc(e.date)}</span>
    <a onclick="go('${esc(e.firmId)}')">${esc(f?f.firm:"?")}</a>
    <span class="muted">${esc(e.course)} \u00B7 ${esc(e.presenter||"presenter TBD")}</span></div>`;}).join("")
    ||'<div class="muted">Nothing scheduled \u2014 that is the problem to fix this week.</div>'}
   <div style="margin-top:8px"><a onclick="location.hash='#/events'">Open L&L Events \u2192</a></div></div>
  <div class="card"><h3>Open follow-ups & to-dos</h3>
   ${fus.map(e=>{const f=firm(e.firmId);return `<div class="frow"><span class="badge b-red">follow-up</span>
    <a onclick="go('${esc(e.firmId)}')">${esc(f?f.firm:"?")}</a><span class="muted">session ${esc(e.date)} \u00B7 due ${esc(fuDue(e))}</span></div>`;}).join("")}
   ${openTodos().slice(0,6).map(td=>{const f=td.firmId?firm(td.firmId):null;
    return `<div class="frow"><span class="pill ${td.due&&td.due<today()?"overdue":""}">${esc(td.due||"no date")}</span>
    <span>${esc(td.t)}</span><span class="muted">${f?esc(f.firm):""}</span></div>`;}).join("")||""}
   <div style="margin-top:8px"><a onclick="location.hash='#/todos'">Open To-Do List \u2192</a></div></div>
  </div>`;
};

let TF={q:"",state:"",tier:"",fit:"",status:""}, sortK="state", sortAsc=true;
V.targets=function(){
  head("Targets","Click a firm to open its record \u00B7 all fields editable there");
  const states=[...new Set(S.firms.map(f=>f.state))].sort();
  let out=S.firms.filter(f=>
    (!TF.state||f.state===TF.state)&&(!TF.tier||f.tier===TF.tier)&&
    (!TF.fit||f.fit===TF.fit)&&(!TF.status||f.status===TF.status)&&
    (!TF.q||[f.firm,f.city,f.type,f.strengths,f.angle,f.rep,f.office,
      (f.notes||[]).map(n=>n.what).join(" ")].join(" ").toLowerCase().includes(TF.q)));
  out.sort((a,b)=>{const va=String(a[sortK]||"").toLowerCase(),vb=String(b[sortK]||"").toLowerCase();
    return (va<vb?-1:va>vb?1:0)*(sortAsc?1:-1);});
  const tc={"Tier 1":"t1","Tier 2":"t2","Tier 3":"t3"};
  document.getElementById("view").innerHTML =
  `<div class="filters">
   <input id="fq" placeholder="Search firm, city, notes\u2026" value="${esc(TF.q)}">
   <select id="fs"><option value="">All states</option>${states.map(s=>`<option ${TF.state===s?"selected":""}>${esc(s)}</option>`).join("")}</select>
   <select id="ft"><option value="">All tiers</option>${["Tier 1","Tier 2","Tier 3"].map(s=>`<option ${TF.tier===s?"selected":""}>${s}</option>`).join("")}</select>
   <select id="ff"><option value="">All courses</option>${["FED","COR","FED+COR"].map(s=>`<option ${TF.fit===s?"selected":""}>${s}</option>`).join("")}</select>
   <select id="fu"><option value="">All statuses</option>${STATUSES.map(s=>`<option ${TF.status===s?"selected":""}>${s}</option>`).join("")}</select>
   <button class="b" id="addFirm">+ Add target</button></div>
  <div class="muted" style="margin-bottom:6px">${out.length} of ${S.firms.length} firms</div>
  <div id="selBar"></div>
  <div class="card" style="padding:6px 10px"><table><thead><tr>
  <th style="width:26px"><input type="checkbox" class="chk" id="selAll"></th>
  <th data-k="state">St</th><th data-k="firm">Firm</th><th data-k="city" class="hidemob">HQ</th>
  <th data-k="fit">Fit</th><th data-k="tier">Tier</th><th data-k="status">Status</th>
  <th class="hidemob">Cadence</th><th data-k="rep" class="hidemob">Rep</th><th data-k="next" class="hidemob">Next action</th>
  </tr></thead><tbody>
  ${out.map(f=>{const fl=flag(f);return `<tr class="rw">
   <td><input type="checkbox" class="chk selRow" data-id="${esc(f.id)}" ${SEL.has(f.id)?"checked":""}></td>
   <td>${esc(f.state)}</td><td><a onclick="go('${esc(f.id)}')">${esc(f.firm)}</a></td>
   <td class="hidemob muted">${esc(f.city)}</td><td>${esc(f.fit)}</td>
   <td class="${tc[f.tier]||""}">${esc(f.tier.replace("Tier ","T"))}</td>
   <td><span class="badge ${SB[f.status]}">${esc(f.status)}</span></td>
   <td class="hidemob"><span class="dot d${fl}"></span><span class="muted">${f.lastTouch?daysSince(f.lastTouch)+"d":"never"}</span></td>
   <td class="hidemob muted">${esc(f.rep)}</td><td class="hidemob muted">${esc(f.next)}</td></tr>`;}).join("")}
  </tbody></table></div>`;
  document.getElementById("fq").addEventListener("input",e=>{TF.q=e.target.value.toLowerCase();V.targets();});
  [["fs","state"],["ft","tier"],["ff","fit"],["fu","status"]].forEach(([id,k])=>
    document.getElementById(id).addEventListener("change",e=>{TF[k]=e.target.value;V.targets();}));
  document.querySelectorAll("th[data-k]").forEach(th=>th.addEventListener("click",()=>{
    const k=th.dataset.k; if(sortK===k)sortAsc=!sortAsc;else{sortK=k;sortAsc=true;} V.targets();}));
  document.getElementById("addFirm").addEventListener("click",openAdd);
  document.getElementById("selAll").addEventListener("change",e=>{
    out.forEach(f=>e.target.checked?SEL.add(f.id):SEL.delete(f.id));V.targets();});
  document.querySelectorAll(".selRow").forEach(c=>c.addEventListener("change",()=>{
    c.checked?SEL.add(c.dataset.id):SEL.delete(c.dataset.id);selBar();}));
  selBar();
};

let SEL=new Set();
function selBar(){
  const el=document.getElementById("selBar"); if(!el)return;
  if(!SEL.size){el.innerHTML="";return;}
  el.innerHTML=`<div class="card" style="padding:10px 14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">
  <b>${SEL.size} selected</b>
  <button class="ghost" id="selExp">\u2913 Export selected CSV</button>
  <button class="danger" id="selDel">Delete selected</button>
  <a id="selClr">Clear</a></div>`;
  document.getElementById("selClr").addEventListener("click",()=>{SEL.clear();V.targets();});
  document.getElementById("selExp").addEventListener("click",()=>{
    const list=S.firms.filter(f=>SEL.has(f.id));
    dl("selected-targets.csv",toCSV(list),"text/csv");});
  document.getElementById("selDel").addEventListener("click",()=>{
    if(!confirm("Delete "+SEL.size+" firm(s) plus their notes, to-dos and events? Export them first if you need to fix and re-import."))return;
    S.firms=S.firms.filter(f=>!SEL.has(f.id));
    S.todos=S.todos.filter(t=>!SEL.has(t.firmId));
    S.events=S.events.filter(e=>!SEL.has(e.firmId));
    SEL.clear();save();V.targets();
    stamp("Deleted \u00B7 "+(USER?"live-synced":"saved locally"),"ok");});
}

window.go=id=>{location.hash="#/firm/"+encodeURIComponent(id);};

V.firm=function(id){
  const f=firm(id); if(!f){location.hash="#/targets";return;}
  head(f.firm, `${esc(f.city)}, ${esc(f.state)} \u00B7 ${esc(f.type)} \u00B7 <a onclick="location.hash='#/targets'">\u2190 back to Targets</a>`);
  const fl=flag(f), ds=f.lastTouch?daysSince(f.lastTouch)+" days ago ("+f.lastTouch+")":"never";
  const web=f.website&&!f.website.includes("verify")
    ?`<a href="https://${esc(f.website)}" target="_blank" rel="noopener">${esc(f.website)}</a>`:esc(f.website||"\u2014");
  const ftodos=S.todos.filter(t=>t.firmId===id);
  const fevents=S.events.filter(e=>e.firmId===id).sort((a,b)=>a.date<b.date?1:-1);
  const F=(k,label,type,opts)=>{
    if(type==="select")return `<div class="fld"><label>${label}</label>
      <select data-fk="${k}">${opts.map(o=>`<option ${o===(f[k]||"")?"selected":""}>${o}</option>`).join("")}</select></div>`;
    if(type==="ta")return `<div class="fld wide"><label>${label}</label><textarea data-fk="${k}">${esc(f[k]||"")}</textarea></div>`;
    return `<div class="fld"><label>${label}</label><input data-fk="${k}" ${type==="date"?'type="date"':""} value="${esc(f[k]||"")}"></div>`;};
  document.getElementById("view").innerHTML =
  `<div class="grid2">
  <div class="card"><h3>Intel</h3>
   <div style="line-height:1.7;font-size:12.5px">
   <b>Website:</b> ${web}<br><b>Sector strengths:</b> ${esc(f.strengths||"\u2014")}<br>
   <b>2025 standing:</b> ${esc(f.standing||"\u2014")}<br><b>Angle:</b> ${esc(f.angle||"\u2014")}<br>
   <b>CEU fit:</b> ${esc(f.fit)} \u00B7 <b>Tier:</b> ${esc(f.tier)}</div></div>
  <div class="card"><h3>Contact cadence</h3>
   <div style="font-size:12.5px;line-height:1.8">
   <span class="dot d${fl}"></span><b>Last touch:</b> ${esc(ds)}<br>
   <b>Next scheduled:</b> <input type="date" data-fk="nextSched" value="${esc(f.nextSched||"")}" style="width:auto">
   </div>
   <div style="margin-top:10px;display:flex;gap:8px">
   <button class="b" id="touch">Touched today</button>
   <button class="danger" id="delFirm">Delete target</button></div></div>
  </div>
  <div class="card"><h3>Record \u2014 all fields editable, autosaves</h3>
   <div class="form">
   ${F("status","Status","select",STATUSES)}
   ${F("course","Course to book","select",["","FED","COR","Either"])}
   ${F("tier","Tier","select",["Tier 1","Tier 2","Tier 3"])}
   ${F("rep","Rep agency")} ${F("office","Target office / city")} ${F("champion","Internal champion")}
   ${F("contact","Contact name")} ${F("title","Contact title")} ${F("email","Email / phone")}
   ${F("outreach","Outreach date","date")} ${F("lldate","L&L date","date")}
   ${F("next","Next action \u2014 no record without one","ta")}
   </div></div>
  <div class="grid2">
  <div class="card"><h3>Notes \u00B7 Date \u2013 Who \u2013 What \u2013 Next</h3>
   <div class="form" style="grid-template-columns:90px 1fr 1fr auto">
   <input id="nWho" placeholder="Who" value="${esc(S.settings.me)}">
   <input id="nWhat" placeholder="What happened">
   <input id="nNext" placeholder="Next step">
   <button class="b" id="nAdd">Add</button></div>
   <div id="nList">${(f.notes||[]).slice().reverse().map((n,i)=>
    `<div class="note-item"><div class="m">${esc(n.d)} \u2013 ${esc(n.who)}
     <span class="x" data-ni="${f.notes.length-1-i}">\u00D7</span></div>
     ${esc(n.what)}${n.next?`<div class="m">\u2192 ${esc(n.next)}</div>`:""}</div>`).join("")
    ||'<div class="muted">No notes yet.</div>'}</div></div>
  <div class="card"><h3>To-do checklist \u00B7 ${ftodos.filter(t=>!t.done).length} open</h3>
   <div class="form" style="grid-template-columns:1fr 130px auto">
   <input id="tdT" placeholder="To-do"><input id="tdD" type="date"><button class="b" id="tdAdd">Add</button></div>
   ${ftodos.map(td=>`<div class="todo-line ${td.done?"done":""}">
    <input type="checkbox" class="chk" data-td="${td.id}" ${td.done?"checked":""}>
    <span class="t" style="flex:1">${esc(td.t)}</span>
    <span class="due ${!td.done&&td.due&&td.due<today()?"overdue":"muted"}">${esc(td.due||"")}</span>
    <span class="x" data-tdx="${td.id}">\u00D7</span></div>`).join("")||'<div class="muted">Nothing open.</div>'}
   <h3 style="margin-top:14px">Sessions for this firm</h3>
   ${fevents.map(e=>`<div class="frow"><span class="pill">${esc(e.date)}</span>
    <span>${esc(e.course)}</span><span class="muted">${esc(e.presenter||"")}</span>
    <span class="badge ${e.status==="Completed"?"b-dgreen":e.status==="Scheduled"?"b-green":"b-gold"}">${esc(e.status)}</span></div>`).join("")
    ||'<div class="muted">None logged \u2014 add from L&L Events.</div>'}</div>
  </div>`;
  document.querySelectorAll("[data-fk]").forEach(inp=>inp.addEventListener("input",()=>{
    f[inp.dataset.fk]=inp.value; save();}));
  document.getElementById("touch").addEventListener("click",()=>{f.lastTouch=today();save();V.firm(id);});
  document.getElementById("delFirm").addEventListener("click",()=>{
    if(!confirm("Delete "+f.firm+" and its notes/to-dos?"))return;
    S.firms=S.firms.filter(x=>x.id!==id);S.todos=S.todos.filter(t=>t.firmId!==id);
    S.events=S.events.filter(e=>e.firmId!==id);save();location.hash="#/targets";});
  document.getElementById("nAdd").addEventListener("click",()=>{
    const what=document.getElementById("nWhat").value.trim(); if(!what)return;
    f.notes.push({d:today(),who:document.getElementById("nWho").value.trim()||S.settings.me,
      what,next:document.getElementById("nNext").value.trim()});
    f.lastTouch=today(); save(); V.firm(id);});
  document.querySelectorAll("[data-ni]").forEach(x=>x.addEventListener("click",()=>{
    f.notes.splice(+x.dataset.ni,1);save();V.firm(id);}));
  document.getElementById("tdAdd").addEventListener("click",()=>{
    const t=document.getElementById("tdT").value.trim(); if(!t)return;
    S.todos.push({id:Date.now()+"",t,firmId:id,due:document.getElementById("tdD").value,done:false});
    save();V.firm(id);});
  document.querySelectorAll("[data-td]").forEach(c=>c.addEventListener("change",()=>{
    const td=S.todos.find(t=>t.id===c.dataset.td);td.done=c.checked;save();V.firm(id);}));
  document.querySelectorAll("[data-tdx]").forEach(x=>x.addEventListener("click",()=>{
    S.todos=S.todos.filter(t=>t.id!==x.dataset.tdx);save();V.firm(id);}));
};

V.cadence=function(){
  head("Cadence","Red rows are today's call list \u00B7 green \u2264"+S.settings.green+
    "d \u00B7 yellow \u2264"+S.settings.yellow+"d \u00B7 red beyond or never");
  const live=S.firms.filter(f=>!["Declined","Dormant"].includes(f.status));
  const rows=live.map(f=>({f,ds:daysSince(f.lastTouch)}))
    .sort((a,b)=>(b.ds??9e9)-(a.ds??9e9));
  const n={g:0,y:0,r:0}; rows.forEach(x=>n[flag(x.f)]++);
  document.getElementById("view").innerHTML =
  `<div class="kpis"><div class="kpi bad"><div class="v">${n.r}</div><div class="l">Red \u2014 call now</div></div>
  <div class="kpi warn"><div class="v">${n.y}</div><div class="l">Yellow</div></div>
  <div class="kpi good"><div class="v">${n.g}</div><div class="l">Green</div></div></div>
  <div class="card" style="padding:6px 10px"><table><thead><tr>
  <th>Firm</th><th class="hidemob">Tier</th><th>Last touch</th><th>Days</th>
  <th class="hidemob">Next sched.</th><th class="hidemob">Priority / reason to call</th><th></th></tr></thead><tbody>
  ${rows.map(({f,ds})=>`<tr class="rw"><td><span class="dot d${flag(f)}"></span><a onclick="go('${esc(f.id)}')">${esc(f.firm)}</a>
   <span class="muted hidemob">\u00B7 ${esc(f.state)}</span></td>
   <td class="hidemob">${esc(f.tier.replace("Tier ","T"))}</td>
   <td class="muted">${esc(f.lastTouch||"never")}</td><td>${ds===null?"\u2014":ds}</td>
   <td class="hidemob muted">${esc(f.nextSched||"")}</td>
   <td class="hidemob muted">${esc(f.next||f.angle||"")}</td>
   <td><button data-t="${esc(f.id)}">Touched today</button></td></tr>`).join("")}
  </tbody></table></div>`;
  document.querySelectorAll("[data-t]").forEach(b=>b.addEventListener("click",()=>{
    firm(b.dataset.t).lastTouch=today();save();V.cadence();}));
};

V.todos=function(){
  head("To-Do List",openTodos().length+" open \u00B7 "+overdueTodos().length+" overdue");
  const opts=S.firms.map(f=>`<option value="${esc(f.id)}">${esc(f.firm)}</option>`).join("");
  const list=S.todos.slice().sort((a,b)=>(a.done?1:0)-(b.done?1:0)||String(a.due||"9999").localeCompare(b.due||"9999"));
  document.getElementById("view").innerHTML =
  `<div class="card"><div class="form" style="grid-template-columns:2fr 1fr 130px auto auto">
  <input id="gT" placeholder="New to-do"><select id="gF"><option value="">\u2014 no firm \u2014</option>${opts}</select>
  <input id="gD" type="date"><button class="b" id="gAdd">Add</button>
  <button class="ghost" id="ics">\u2913 Outlook (.ics)</button></div></div>
  <div class="card">${list.map(td=>{const f=td.firmId?firm(td.firmId):null;
   return `<div class="todo-line ${td.done?"done":""}">
   <input type="checkbox" class="chk" data-td="${td.id}" ${td.done?"checked":""}>
   <span class="t" style="flex:1">${esc(td.t)}</span>
   ${f?`<a onclick="go('${esc(f.id)}')">${esc(f.firm)}</a>`:""}
   <span class="due ${!td.done&&td.due&&td.due<today()?"overdue":"muted"}">${esc(td.due||"")}</span>
   <span class="x" data-tdx="${td.id}">\u00D7</span></div>`;}).join("")
   ||'<div class="muted">Nothing open \u2014 add to-dos here or from any firm page.</div>'}</div>`;
  document.getElementById("gAdd").addEventListener("click",()=>{
    const t=document.getElementById("gT").value.trim();if(!t)return;
    S.todos.push({id:Date.now()+"",t,firmId:document.getElementById("gF").value||null,
      due:document.getElementById("gD").value,done:false});save();V.todos();});
  document.querySelectorAll("[data-td]").forEach(c=>c.addEventListener("change",()=>{
    S.todos.find(t=>t.id===c.dataset.td).done=c.checked;save();V.todos();}));
  document.querySelectorAll("[data-tdx]").forEach(x=>x.addEventListener("click",()=>{
    S.todos=S.todos.filter(t=>t.id!==x.dataset.tdx);save();V.todos();}));
  document.getElementById("ics").addEventListener("click",()=>{
    const lines=["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//XtraLight//ProspectOS//EN"];
    openTodos().filter(t=>t.due).forEach(t=>{const f=t.firmId?firm(t.firmId):null;
      const d=t.due.replace(/-/g,"");
      lines.push("BEGIN:VEVENT","UID:"+t.id+"@prospectos","DTSTART;VALUE=DATE:"+d,
        "SUMMARY:"+(f?"["+f.firm+"] ":"")+t.t.replace(/[,;\\]/g," "),"END:VEVENT");});
    lines.push("END:VCALENDAR");
    dl("prospect-os-todos.ics",lines.join("\r\n"),"text/calendar");});
};

V.events=function(){
  head("L&L Events","Every delivered session needs follow-up within 5 business days");
  const opts=S.firms.map(f=>`<option value="${esc(f.id)}">${esc(f.firm)}</option>`).join("");
  const list=S.events.slice().sort((a,b)=>a.date<b.date?1:-1);
  document.getElementById("view").innerHTML =
  `<div class="card"><div class="form" style="grid-template-columns:130px 2fr 1fr 1fr 90px 1fr auto">
  <input id="eD" type="date" value="${today()}"><select id="eF">${opts}</select>
  <select id="eC"><option>FED</option><option>COR</option><option>F&B</option></select>
  <input id="eP" placeholder="Presenter"><input id="eA" placeholder="Att." type="number">
  <select id="eFmt"><option>In Person</option><option>Virtual</option></select>
  <button class="b" id="eAdd">+ Log event</button></div></div>
  <div class="card" style="padding:6px 10px"><table><thead><tr>
  <th>Date</th><th>Firm</th><th class="hidemob">Course</th><th class="hidemob">Presenter</th>
  <th class="hidemob">Att.</th><th>Follow-up due</th><th>Status</th><th></th></tr></thead><tbody>
  ${list.map((e,i)=>{const f=firm(e.firmId);const due=fuDue(e);
   const late=e.status!=="Completed"&&e.status!=="Cancelled"&&e.status!=="Converted to Spec Activity"
     &&e.status!=="Scheduled"&&due&&due<today();
   return `<tr class="rw"><td>${esc(e.date)}</td>
   <td><a onclick="go('${esc(e.firmId)}')">${esc(f?f.firm:"?")}</a></td>
   <td class="hidemob">${esc(e.course)}</td><td class="hidemob">${esc(e.presenter||"")}</td>
   <td class="hidemob">${esc(e.attendees||"")}</td>
   <td class="${late?"overdue":"muted"}">${esc(due)}</td>
   <td><select data-ev="${i}">${EVSTATUS.map(s=>`<option ${e.status===s?"selected":""}>${s}</option>`).join("")}</select></td>
   <td><span class="x" data-evx="${i}">\u00D7</span></td></tr>`;}).join("")}
  </tbody></table>${list.length?"":'<div class="muted" style="padding:10px">No events yet \u2014 log one when a session is scheduled.</div>'}</div>`;
  document.getElementById("eAdd").addEventListener("click",()=>{
    const fidv=document.getElementById("eF").value;if(!fidv)return;
    S.events.push({date:document.getElementById("eD").value,firmId:fidv,
      course:document.getElementById("eC").value,presenter:document.getElementById("eP").value,
      attendees:document.getElementById("eA").value,format:document.getElementById("eFmt").value,
      fu:"",status:"Scheduled"});
    const f=firm(fidv); f.status="Scheduled"; f.lldate=document.getElementById("eD").value;
    save();V.events();});
  document.querySelectorAll("[data-ev]").forEach(s=>s.addEventListener("change",()=>{
    const e=list[+s.dataset.ev];e.status=s.value;
    if(s.value==="Completed"){const f=firm(e.firmId);if(f)f.status="Presented";}
    save();V.events();}));
  document.querySelectorAll("[data-evx]").forEach(x=>x.addEventListener("click",()=>{
    const e=list[+x.dataset.evx];S.events=S.events.filter(v=>v!==e);save();V.events();}));
};

V.reports=function(){
  head("Reports","Exports exactly what the data says \u00B7 CSV");
  document.getElementById("view").innerHTML =
  `<div class="card"><h3>Target scorecard</h3>
  <div class="help">Firm, state, tier, fit, status, rep, cadence, next action, latest note \u2014 the leadership readout.</div>
  <button class="b" id="ex1" style="margin-top:8px">\u2913 Export targets CSV</button></div>
  <div class="card"><h3>L&L event log</h3>
  <div class="help">All sessions with follow-up state \u2014 proof of program motion.</div>
  <button class="b" id="ex2" style="margin-top:8px">\u2913 Export events CSV</button></div>`;
  document.getElementById("ex1").addEventListener("click",()=>{
    const rows=[["State","Firm","City","Tier","Fit","Status","Rep","Last touch","Days since","Next action","Latest note"]];
    S.firms.forEach(f=>{const n=f.notes[f.notes.length-1];
      rows.push([f.state,f.firm,f.city,f.tier,f.fit,f.status,f.rep,f.lastTouch,
        f.lastTouch?daysSince(f.lastTouch):"",f.next,n?`${n.d} - ${n.who} - ${n.what} - ${n.next}`:""]);});
    dl("targets-scorecard.csv",rows.map(r=>r.map(csvCell).join(",")).join("\r\n"),"text/csv");});
  document.getElementById("ex2").addEventListener("click",()=>{
    const rows=[["Date","Firm","Course","Presenter","Attendees","Format","Follow-up due","Status"]];
    S.events.forEach(e=>{const f=firm(e.firmId);
      rows.push([e.date,f?f.firm:"",e.course,e.presenter,e.attendees,e.format,fuDue(e),e.status]);});
    dl("ll-events.csv",rows.map(r=>r.map(csvCell).join(",")).join("\r\n"),"text/csv");});
};

V.settings=function(){
  head("Settings","Sync, thresholds, backup");
  const st=S.settings;
  document.getElementById("view").innerHTML =
  `<div class="card"><h3>Sync layers</h3>
  <div class="help"><b>Live sync (Firebase):</b> sign in top-right \u2014 same accounts as Channel OS \u2014 and every
  edit syncs across devices automatically within seconds. If you see a permission error, add a
  <b>prospectos</b> rule in Firebase \u2192 Firestore \u2192 Rules, mirroring your channelos rule.<br><br>
  <b>Publish workbook (GitHub):</b> writes <b>data/prospecting.json</b> (backup) and refreshes
  <b>data/targets.csv</b> so the Excel workbook rebuild stays current. Token: GitHub \u2192 Settings \u2192
  Developer settings \u2192 Fine-grained tokens \u2192 this repo only, Contents = Read and write.</div>
  <div class="form" style="margin-top:10px">
  <div class="fld"><label>Owner</label><input id="sOwner" value="${esc(st.owner)}"></div>
  <div class="fld"><label>Repo</label><input id="sRepo" value="${esc(st.repo)}"></div>
  <div class="fld"><label>Branch</label><input id="sBranch" value="${esc(st.branch)}"></div>
  <div class="fld"><label>Token</label><input id="sToken" type="password" value="${esc(TOKEN)}" placeholder="github_pat_\u2026"></div>
  <div class="fld"><label>Your initials (notes)</label><input id="sMe" value="${esc(st.me)}"></div>
  <div class="fld"><label>&nbsp;</label><label style="text-transform:none"><input type="checkbox" class="chk" id="sRem" ${st.remember?"checked":""}> Remember token on this device</label></div>
  </div></div>
  <div class="card"><h3>Cadence thresholds</h3>
  <div class="form"><div class="fld"><label>Green \u2264 days</label><input id="sG" type="number" value="${st.green}"></div>
  <div class="fld"><label>Yellow \u2264 days</label><input id="sY" type="number" value="${st.yellow}"></div></div></div>
  <div class="card"><h3>Import history</h3>
  <div class="help">Every bulk import is a batch \u2014 remove a batch to undo a bad import. Firms added
  singly or shipped with the app are untouched.</div>
  <div style="margin-top:8px">
  ${(S.imports||[]).slice().reverse().map(b=>{const left=S.firms.filter(f=>f.batch===b.id).length;
    return `<div class="frow"><span class="pill">${esc(b.ts)}</span><span>${esc(b.label)}</span>
    <span class="muted">${b.count} imported \u00B7 ${left} still in list</span>
    ${left?`<button class="danger" data-ib="${b.id}">Remove ${left}</button>`:'<span class="muted">cleared</span>'}</div>`;}).join("")
    ||'<div class="muted">No bulk imports yet.</div>'}
  </div></div>
  <div class="card"><h3>Move data between devices</h3>
  <div class="help">Download a backup here, restore it on the other device \u2014 or just use cloud sync above.</div>
  <div style="display:flex;gap:8px;margin-top:8px">
  <button class="b" id="bk">\u2913 Download backup</button>
  <button class="ghost" id="rs">\u2912 Restore backup\u2026</button>
  <input type="file" id="rsf" accept=".json" style="display:none">
  <button class="danger" id="reset">Reset to shipped dataset</button></div></div>`;
  const bind=(id,k,num)=>document.getElementById(id).addEventListener("input",e=>{
    st[k]=num?+e.target.value:e.target.value;save();});
  bind("sOwner","owner");bind("sRepo","repo");bind("sBranch","branch");bind("sMe","me");
  bind("sG","green",1);bind("sY","yellow",1);
  document.getElementById("sToken").addEventListener("input",e=>{TOKEN=e.target.value.trim();save();});
  document.getElementById("sRem").addEventListener("change",e=>{st.remember=e.target.checked;save();});
  document.querySelectorAll("[data-ib]").forEach(b=>b.addEventListener("click",()=>{
    const ids=new Set(S.firms.filter(f=>f.batch===b.dataset.ib).map(f=>f.id));
    if(!confirm("Remove "+ids.size+" firm(s) from this import, plus their notes/to-dos/events?"))return;
    S.firms=S.firms.filter(f=>f.batch!==b.dataset.ib);
    S.todos=S.todos.filter(t=>!ids.has(t.firmId));
    S.events=S.events.filter(e=>!ids.has(e.firmId));
    save();V.settings();stamp("Import removed \u00B7 "+(USER?"live-synced":"saved locally"),"ok");}));
  document.getElementById("bk").addEventListener("click",()=>
    dl("prospect-os-backup.json",JSON.stringify(S,null,1),"application/json"));
  document.getElementById("rs").addEventListener("click",()=>document.getElementById("rsf").click());
  document.getElementById("rsf").addEventListener("change",e=>{
    const r=new FileReader();r.onload=()=>{try{S=JSON.parse(r.result);save();render();
      stamp("Backup restored.","ok");}catch(x){stamp("Bad backup file.","err")}};
    r.readAsText(e.target.files[0]);});
  document.getElementById("reset").addEventListener("click",()=>{
    if(!confirm("Reset ALL data to the shipped 126-firm dataset? Local notes are lost."))return;
    S=seedState();save();render();});
};

V.guide=function(){
  head("User Guide","The operating rhythm");
  document.getElementById("view").innerHTML=`<div class="card guide">
  <h4 class="gsec">Daily \u2014 10 minutes</h4><ol>
  <li><b>Cadence:</b> work the red rows top-down. Call or email, then hit <b>Touched today</b>.</li>
  <li>Clear any to-do dated today or earlier (shown red).</li>
  <li>Log everything the moment it happens \u2014 notes take 15 seconds on a phone.</li></ol>
  <h4 class="gsec">Weekly \u2014 30 minutes, Monday</h4><ol>
  <li><b>Overview:</b> read Needs Attention; open the coldest Tier 1s and set next actions.</li>
  <li><b>L&L Events:</b> close open follow-ups \u2014 5 business days, no exceptions.</li>
  <li><b>Targets:</b> every firm in Outreach Sent or In Scheduling gets a dated next step.</li>
  <li>Signed in? Every edit already synced live. Hit <b>Publish workbook</b> weekly so the Excel file catches up.</li></ol>
  <h4 class="gsec">Data hygiene rules</h4><ul>
  <li>Notes format: <b>Date \u2013 Who \u2013 What \u2013 Next.</b> No note without a next.</li>
  <li>Statuses drive the dashboard \u2014 keep them true, not hopeful.</li>
  <li>Cadence flags: green \u2264 ${S.settings.green}d since touch \u00B7 yellow \u2264 ${S.settings.yellow}d \u00B7 red beyond or never. Red rows are the day's call list.</li>
  <li>A session isn't real until it's in L&L Events with a date.</li></ul>
  <h4 class="gsec">Good to know</h4><ul>
  <li>Everything saves to this browser automatically as you type \u2014 offline included.</li>
  <li>Sign in once per device for live sync \u2014 same login as Channel OS. <b>Publish workbook</b> refreshes the Excel side.</li>
  <li>Click any firm name anywhere to jump to its record.</li>
  <li>Reports export exactly what's on screen as CSV. To-dos export to Outlook as .ics.</li></ul></div>`;
};

/* ================= cloud sync ================= */
function csvCell(v){v=String(v??"");return /[",\n\r]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v;}
function toCSV(list){
  const hdr=["State (HQ)","Firm","HQ City","Firm Type","Website","Gov Sector Strengths",
  "2025 Standing / Source","CEU Fit","Priority","Angle / Entry Notes","Assigned Rep Agency",
  "Status","Course to Book","Target Office / City","Contact Name","Contact Title",
  "Contact Email / Phone","Outreach Date","L&L Date","Next Action","Notes"];
  const rows=[hdr];
  (list||S.firms).slice().sort((a,b)=>(a.state+a.firm).localeCompare(b.state+b.firm)).forEach(f=>{
    const n=f.notes[f.notes.length-1];
    rows.push([f.state,f.firm,f.city,f.type,f.website,f.strengths,f.standing,f.fit,f.tier,
      f.angle,f.rep,f.status,f.course,f.office,f.contact,f.title,f.email,f.outreach,
      f.lldate,f.next,n?`${n.d} - ${n.who} - ${n.what}${n.next?" - "+n.next:""}`:""]);});
  return rows.map(r=>r.map(csvCell).join(",")).join("\r\n")+"\r\n";
}
function b64(s){const b=new TextEncoder().encode(s);let x="";
  for(let i=0;i<b.length;i+=8192)x+=String.fromCharCode.apply(null,b.subarray(i,i+8192));
  return btoa(x);}
function api(path){const st=S.settings;
  return `https://api.github.com/repos/${st.owner}/${st.repo}/contents/${path}`;}
async function putFile(path,content,msg,H){
  let sha; const g=await fetch(api(path)+"?ref="+S.settings.branch,{headers:H});
  if(g.ok)sha=(await g.json()).sha;
  const body={message:msg,content:b64(content),branch:S.settings.branch};
  if(sha)body.sha=sha;
  const p=await fetch(api(path),{method:"PUT",headers:{...H,"Content-Type":"application/json"},
    body:JSON.stringify(body)});
  if(!p.ok)throw new Error(path+" \u2192 "+p.status);
}
async function cloudSave(){
  const st=S.settings;
  if(!st.owner||!st.repo||!TOKEN){stamp("Add owner/repo/token in Settings.","err");
    location.hash="#/settings";return;}
  const H={Authorization:"Bearer "+TOKEN,Accept:"application/vnd.github+json"};
  try{stamp("Saving to cloud\u2026");
    const state={...S,token:""};
    await putFile("data/prospecting.json",JSON.stringify(state,null,1),"Prospect OS: state sync",H);
    await putFile("data/targets.csv",toCSV(),"Prospect OS: roster refresh from field notes",H);
    stamp("Cloud saved \u00B7 workbook rebuild running \u00B7 "+new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"}),"ok");
  }catch(e){stamp("Cloud save failed: "+e.message+(e.message.includes("401")?" (token?)":""),"err");}
}
async function cloudLoad(){
  const st=S.settings;
  if(!st.owner||!st.repo||!TOKEN){stamp("Add owner/repo/token in Settings.","err");
    location.hash="#/settings";return;}
  const H={Authorization:"Bearer "+TOKEN,Accept:"application/vnd.github+json"};
  try{stamp("Loading from cloud\u2026");
    const g=await fetch(api("data/prospecting.json")+"?ref="+st.branch,{headers:H});
    if(g.status===404){stamp("No cloud state yet \u2014 hit Save to cloud first.","err");return;}
    if(!g.ok)throw new Error(g.status);
    const j=await g.json();
    const bytes=Uint8Array.from(atob(j.content.replace(/\n/g,"")),c=>c.charCodeAt(0));
    const inc=JSON.parse(new TextDecoder().decode(bytes));
    inc.settings=Object.assign({},S.settings,inc.settings||{});
    S=inc; save(); render(); stamp("Cloud state loaded.","ok");
  }catch(e){stamp("Cloud load failed: "+e.message,"err");}
}
function dl(name,content,type){
  const a=document.createElement("a");
  a.href=URL.createObjectURL(new Blob([content],{type}));a.download=name;a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href),5000);}

/* ================= add / import targets ================= */
const HDRMAP={"state":"state","state (hq)":"state","firm":"firm","hq city":"city","city":"city",
"firm type":"type","type":"type","website":"website","gov sector strengths":"strengths","strengths":"strengths",
"2025 standing / source":"standing","2025 standing":"standing","standing":"standing","ceu fit":"fit","fit":"fit",
"priority":"tier","tier":"tier","angle / entry notes":"angle","angle":"angle","assigned rep agency":"rep",
"rep agency":"rep","rep":"rep","status":"status","course to book":"course","course":"course",
"target office / city":"office","office":"office","contact name":"contact","contact":"contact",
"contact title":"title","title":"title","contact email / phone":"email","email / phone":"email","email":"email",
"outreach date":"outreach","outreach":"outreach","l&l date":"lldate","ll date":"lldate",
"next action":"next","next":"next","notes":"notes","latest note":"notes"};
function parseCSV(text){const rows=[[""]];let r=0,c=0,q=false;
  for(let i=0;i<text.length;i++){const ch=text[i];
    if(q){if(ch==='"'){if(text[i+1]==='"'){rows[r][c]+='"';i++;}else q=false;}else rows[r][c]+=ch;}
    else{if(ch==='"')q=true;else if(ch===','){rows[r].push("");c++;}
      else if(ch==='\n'){rows.push([""]);r++;c=0;}else if(ch!=='\r')rows[r][c]+=ch;}}
  if(rows.length&&rows[rows.length-1].length===1&&rows[rows.length-1][0]==="")rows.pop();
  return rows;}
function parseBulk(text){
  text=text.replace(/\r\n/g,"\n").trim(); if(!text)return [];
  let grid;
  if(text.includes("\t"))grid=text.split("\n").map(l=>l.split("\t").map(s=>s.trim()));
  else grid=parseCSV(text);
  if(!grid.length)return [];
  let cols=["state","firm","city","website","tier","fit"],start=0;
  const h=grid[0].map(x=>String(x).toLowerCase().trim());
  if(h.some(x=>HDRMAP[x]==="firm")){cols=h.map(x=>HDRMAP[x]||null);start=1;}
  const out=[];
  for(let i=start;i<grid.length;i++){const row=grid[i];const o={};
    cols.forEach((k,j)=>{if(k&&row[j]!==undefined)o[k]=String(row[j]).trim();});
    if(!o.firm)continue;
    o.state=(o.state||"").toUpperCase()||"??";
    if(o.tier&&!/^Tier /i.test(o.tier))o.tier="Tier "+o.tier.replace(/^T/i,"");
    out.push(o);}
  return out;}
function newFirm(o){
  const f={state:"",firm:"",city:"",type:"",website:"",strengths:"",standing:"",fit:"FED",tier:"Tier 2",
    angle:"",rep:"",status:"Not Started",course:"",office:"",contact:"",title:"",email:"",outreach:"",
    lldate:"",next:"",lastTouch:"",nextSched:"",champion:"",notes:[]};
  Object.entries(o).forEach(([k,v])=>{if(v&&k!=="notes")f[k]=v;});
  if(o.notes)f.notes=[{d:today(),who:S.settings.me,what:o.notes,next:""}];
  if(!STATUSES.includes(f.status))f.status="Not Started";
  if(!["Tier 1","Tier 2","Tier 3"].includes(f.tier))f.tier="Tier 2";
  f.id=fid(f);return f;}
let BULK=[];
function openAdd(){document.getElementById("addm").style.display="flex";}
function bindAdd(){
  const $=id=>document.getElementById(id);
  $("amX").addEventListener("click",()=>$("addm").style.display="none");
  $("amTab1").addEventListener("click",()=>{$("amSingle").style.display="";$("amBulk").style.display="none";
    $("amTab1").className="b";$("amTab2").className="ghost";});
  $("amTab2").addEventListener("click",()=>{$("amSingle").style.display="none";$("amBulk").style.display="";
    $("amTab2").className="b";$("amTab1").className="ghost";});
  $("aGo").addEventListener("click",()=>{
    const o={state:$("aState").value.trim().toUpperCase(),firm:$("aFirm").value.trim(),
      city:$("aCity").value.trim(),type:$("aType").value.trim(),website:$("aWeb").value.trim(),
      tier:$("aTier").value,fit:$("aFit").value,rep:$("aRep").value.trim(),angle:$("aAngle").value.trim()};
    if(!o.firm||!o.state){$("aErr").textContent="State and firm are required.";return;}
    const f=newFirm(o);
    if(firm(f.id)){$("aErr").textContent="Already in the list: "+f.firm+" ("+f.state+").";return;}
    S.firms.push(f);save();
    ["aState","aFirm","aCity","aType","aWeb","aRep","aAngle"].forEach(i=>$(i).value="");
    $("aErr").textContent="";$("addm").style.display="none";go(f.id);});
  $("bFile").addEventListener("change",e=>{const fl=e.target.files[0];if(!fl)return;
    const rd=new FileReader();rd.onload=()=>{$("bTxt").value=rd.result;preview();};rd.readAsText(fl);});
  $("bParse").addEventListener("click",preview);
  function preview(){
    BULK=parseBulk($("bTxt").value);
    if(!BULK.length){$("bPrev").innerHTML='<div class="muted">Nothing parsed \u2014 check the format.</div>';return;}
    const dups=BULK.filter(o=>firm(fid(o))).length;
    $("bPrev").innerHTML=`<div class="muted" style="margin-bottom:6px">${BULK.length} rows parsed \u00B7
      ${BULK.length-dups} new \u00B7 ${dups} already in list</div>
    <div style="max-height:220px;overflow:auto"><table><thead><tr>
    <th>St</th><th>Firm</th><th>City</th><th>Tier</th><th>Fit</th><th></th></tr></thead><tbody>
    ${BULK.slice(0,100).map(o=>`<tr><td>${esc(o.state)}</td><td>${esc(o.firm)}</td><td>${esc(o.city||"")}</td>
     <td>${esc(o.tier||"Tier 2")}</td><td>${esc(o.fit||"FED")}</td>
     <td>${firm(fid(o))?'<span class="badge b-gold">exists</span>':'<span class="badge b-green">new</span>'}</td></tr>`).join("")}
    </tbody></table></div>
    <button class="b" id="bGo" style="margin-top:10px">Import</button>`;
    document.getElementById("bGo").addEventListener("click",()=>{
      let added=0,updated=0;const upd=document.getElementById("bUpd").checked;
      const bid="b"+Date.now();
      const label=(document.getElementById("bFile").files[0]&&document.getElementById("bFile").files[0].name)||"pasted rows";
      BULK.forEach(o=>{const ex=firm(fid(o));
        if(ex){if(upd){Object.entries(o).forEach(([k,v])=>{
          if(v&&k!=="notes"&&k!=="firm"&&k!=="state")ex[k]=v;});updated++;}return;}
        const nf=newFirm(o);nf.batch=bid;S.firms.push(nf);added++;});
      if(added)S.imports.push({id:bid,ts:new Date().toLocaleString(),label,count:added});
      save();$("addm").style.display="none";$("bPrev").innerHTML="";$("bTxt").value="";$("bFile").value="";
      stamp(`Imported ${added} new${upd&&updated?", updated "+updated:""}${USER?" \u00B7 live-synced":""}`,"ok");
      if((location.hash||"").includes("targets"))V.targets();else location.hash="#/targets";});
  }
}

/* ================= Firebase live sync (same project as Channel OS) ================= */
const FB_CONFIG={apiKey:"AIzaSyBArCz3EwRoroQiz8TmlvXP0LiraYoUFD4",
authDomain:"agent-dashboard-95a62.firebaseapp.com",projectId:"agent-dashboard-95a62",
storageBucket:"agent-dashboard-95a62.firebasestorage.app",
messagingSenderId:"743932431643",appId:"1:743932431643:web:a5df01215a7b5faac157be"};
let FB=null,USER=null,UNSUB=null,pushT=null,applyingRemote=false;
const fbRef=()=>FB.db.collection("prospectos").doc("data");
function schedulePush(){
  if(!FB||!USER||applyingRemote)return;
  clearTimeout(pushT);
  pushT=setTimeout(()=>{fbRef().set({json:JSON.stringify({...S,token:""}),updated:Date.now(),by:USER.email})
    .then(()=>stamp("Live sync \u00B7 "+USER.email,"ok"))
    .catch(e=>stamp("Sync error: "+e.message+
      (String(e.message).toLowerCase().includes("permission")?" \u2014 add 'prospectos' to Firestore rules":""),"err"));
  },1200);
}
function showLogin(on){document.getElementById("login").style.display=on?"flex":"none";}
function syncUI(){
  const chip=document.getElementById("userChip"),btn=document.getElementById("signBtn");
  if(USER){chip.style.display="";chip.textContent=USER.email;btn.textContent="Sign out";}
  else{chip.style.display="none";btn.textContent="Sign in";stamp("Local only \u00B7 sign in for live sync");}
}
function bootFB(start){
  if(!(window.firebase&&window.firebase.auth&&window.firebase.firestore)){
    if(Date.now()-start<6000){setTimeout(()=>bootFB(start),120);return;}
    stamp("Local only \u00B7 Firebase SDK unavailable");return;}
  if(!firebase.apps.length)firebase.initializeApp(FB_CONFIG);
  FB={auth:firebase.auth(),db:firebase.firestore()};
  FB.auth.onAuthStateChanged(u=>{
    if(UNSUB){UNSUB();UNSUB=null;}
    USER=u||null; syncUI();
    if(!u){if(!localStorage.getItem("pos_localonly"))showLogin(true);return;}
    showLogin(false);
    UNSUB=fbRef().onSnapshot(snap=>{
      if(snap.metadata.hasPendingWrites)return;
      if(snap.exists){
        try{
          const inc=JSON.parse(snap.data().json);
          inc.settings=Object.assign({},S.settings,inc.settings||{});
          applyingRemote=true; S=inc; save(); applyingRemote=false;
          render(); stamp("Live sync \u00B7 "+u.email,"ok");
        }catch(e){stamp("Cloud data unreadable: "+e.message,"err");}
      }else{
        fbRef().set({json:JSON.stringify({...S,token:""}),updated:Date.now(),by:u.email});
        stamp("Cloud seeded from this device \u00B7 "+u.email,"ok");
      }
    },err=>stamp("Sync error: "+err.message+
      (String(err.message).toLowerCase().includes("permission")?" \u2014 add 'prospectos' to Firestore rules":""),"err"));
  });
}

/* ================= boot ================= */
function render(){
  renderNav();
  const parts=location.hash.replace(/^#\//,"").split("/");
  const v=parts[0]||"overview";
  if(v==="firm"&&parts[1]){V.firm(decodeURIComponent(parts[1]));return;}
  (V[v]||V.overview)();
}
document.getElementById("cloudSave").addEventListener("click",cloudSave);
document.getElementById("cloudLoad").addEventListener("click",cloudLoad);
document.getElementById("signBtn").addEventListener("click",()=>{
  if(USER&&FB){FB.auth.signOut();return;}
  localStorage.removeItem("pos_localonly");showLogin(true);});
document.getElementById("lgGo").addEventListener("click",async()=>{
  const err=document.getElementById("lgErr");err.textContent="";
  if(!FB){err.textContent="Firebase unavailable on this network.";return;}
  try{await FB.auth.signInWithEmailAndPassword(
    document.getElementById("lgE").value.trim(),document.getElementById("lgP").value);}
  catch(x){err.textContent=x.message;}});
document.getElementById("lgSkip").addEventListener("click",()=>{
  localStorage.setItem("pos_localonly","1");showLogin(false);syncUI();});
stamp("Local data \u00B7 autosaves as you type");
render();
bindAdd();
bootFB(Date.now());
</script>
</body>
</html>
"""


def main():
    rows = load()
    with open(LOGO_PATH, "rb") as f:
        logo64 = base64.b64encode(f.read()).decode("ascii")
    html = (TEMPLATE
            .replace("__DATA__", json.dumps(rows, ensure_ascii=False))
            .replace("__LOGO__", logo64)
            .replace("__DATE__", date.today().strftime("%Y-%m-%d")))
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Built {OUT_PATH}: {len(rows)} firms, {os.path.getsize(OUT_PATH)//1024} KB")


if __name__ == "__main__":
    main()
