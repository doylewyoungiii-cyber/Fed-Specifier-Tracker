#!/usr/bin/env python3
"""Generate index.html - XtraLight-branded, *editable* dashboard of the CEU
L&L target pipeline.

Each firm expands into a field-notes form. Edits stage in the browser (and
survive refresh/offline via a local draft cache), then a single Commit pushes
them to data/targets.csv through the GitHub Contents API - which triggers the
Action to rebuild the workbook and this page.

Usage:  python scripts/build_site.py
Output: index.html (repo root)
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
<title>XtraLight | CEU Lunch &amp; Learn Command Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root{--blue:#0079C1;--black:#000;--green:#5D9732;--gold:#C49F06;--grey:#58595B;
--lt:#F4F5F6;--tint:#F0F7FC;--line:#E2E6E9;}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Montserrat',Arial,sans-serif;color:#111;background:#fff}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
header{border-bottom:4px solid var(--blue);background:#fff;position:sticky;top:0;z-index:20}
.hrow{display:flex;align-items:center;justify-content:space-between;padding:12px 0;gap:16px;flex-wrap:wrap}
.hrow img{height:44px}
.hctl{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
button{font-family:inherit;font-weight:700;font-size:12.5px;border:none;border-radius:8px;
padding:9px 14px;cursor:pointer}
.btn-blue{background:var(--blue);color:#fff}.btn-blue:disabled{background:#B9CFDD;cursor:default}
.btn-ghost{background:var(--lt);color:#333}
.msg{font-size:12px;font-weight:600;color:var(--grey)}
.msg.ok{color:var(--green)}.msg.err{color:#B02A2A}
h2{font-size:13px;font-weight:800;letter-spacing:.12em;color:var(--blue);margin:24px 0 12px}
.sub{font-size:12px;color:var(--grey);margin-top:4px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(125px,1fr));gap:12px;margin-top:20px}
.kpi{background:var(--tint);border-radius:10px;padding:13px 15px}
.kpi .n{font-size:25px;font-weight:900;color:var(--blue)}
.kpi .l{font-size:10px;font-weight:700;color:var(--grey);letter-spacing:.06em;text-transform:uppercase}
.funnel .row{display:flex;align-items:center;gap:10px;margin:6px 0}
.funnel .lab{width:118px;font-size:12px;font-weight:600}
.funnel .bar{height:15px;border-radius:8px;background:var(--blue);min-width:2px}
.funnel .ct{font-size:12px;font-weight:700;color:var(--grey)}
.controls{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0 8px}
.controls input,.controls select{font-family:inherit;font-size:13px;padding:8px 10px;
border:1.5px solid var(--line);border-radius:8px;background:#fff}
.controls input{flex:1;min-width:180px}
.count{font-size:12px;color:var(--grey);margin:4px 0 8px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{background:var(--blue);color:#fff;text-align:left;padding:9px 10px;font-size:11px;
letter-spacing:.05em;cursor:pointer;user-select:none}
td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
tr.main:hover{background:var(--tint);cursor:pointer}
tr.main.edited td:first-child{box-shadow:inset 4px 0 0 var(--gold)}
tr.t1 td.firm{font-weight:700}
.badge{display:inline-block;padding:2px 9px;border-radius:9px;font-size:10.5px;font-weight:700;white-space:nowrap}
.b-grey{background:#ECEDEE;color:#555}.b-blue{background:#DCEFFB;color:#075E92}
.b-gold{background:#F6ECC8;color:#7A6404}.b-green{background:#DDEFD2;color:#3D6B1D}
.b-dgreen{background:#5D9732;color:#fff}.b-dim{background:#F1F1F1;color:#999}
.tierchip{font-weight:800;font-size:11px}
.tier1{color:var(--blue)}.tier2{color:var(--gold)}.tier3{color:var(--grey)}
tr.detail td{background:#FAFBFC;padding:14px 16px;border-left:3px solid var(--blue)}
.intel{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:6px 24px;
font-size:12px;color:#333;margin-bottom:12px}
.intel b{color:#000}
.fnh{font-size:11px;font-weight:800;letter-spacing:.1em;color:var(--blue);margin:6px 0 8px}
.form{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px 14px}
.fld label{display:block;font-size:10px;font-weight:700;letter-spacing:.05em;color:var(--grey);
text-transform:uppercase;margin-bottom:3px}
.fld input,.fld select,.fld textarea{width:100%;font-family:inherit;font-size:12.5px;
padding:7px 9px;border:1.5px solid var(--line);border-radius:7px;background:#fff}
.fld textarea{min-height:64px;resize:vertical}
.fld.wide{grid-column:1/-1}
.fld input:focus,.fld select:focus,.fld textarea:focus{outline:none;border-color:var(--blue)}
a{color:var(--blue);text-decoration:none;font-weight:600}
footer{margin-top:36px;background:#000;color:#fff}
footer .frow{display:flex;justify-content:space-between;align-items:center;padding:16px 0;
flex-wrap:wrap;gap:8px;font-size:12px}
footer .tag{font-weight:700}
footer .co{color:#92B6C7}
.note{font-size:11px;color:var(--grey);font-style:italic;margin-top:8px}
#setup{display:none;background:var(--tint);border:1.5px solid var(--line);border-radius:10px;
padding:16px;margin-top:14px}
#setup .form{margin-top:8px}
#setup p{font-size:12px;color:#333;line-height:1.5}
.hidemob{}
@media(max-width:640px){.hidemob{display:none}}
</style>
</head>
<body>
<header><div class="wrap"><div class="hrow">
<img src="data:image/png;base64,__LOGO__" alt="XtraLight LED Lighting Solutions">
<div class="hctl">
<span class="msg" id="msg"></span>
<button class="btn-ghost" id="setupBtn">&#9881; Setup</button>
<button class="btn-ghost" id="discardBtn" style="display:none">Discard</button>
<button class="btn-blue" id="commitBtn" disabled>Commit changes</button>
</div>
</div></div></header>

<div class="wrap">
<div id="setup">
<b style="font-size:13px">One-time sync setup (per device)</b>
<p>To push field notes from this page into the repo, create a fine-grained personal access token at
GitHub &rarr; Settings &rarr; Developer settings &rarr; Fine-grained tokens: Repository access =
<b>only this repo</b>, Permissions &rarr; Contents = <b>Read and write</b>. Treat it like a password.
Without a token you can still take notes &mdash; they stay saved on this device until you commit.</p>
<div class="form">
<div class="fld"><label>GitHub owner (user/org)</label><input id="cfgOwner" placeholder="your-username"></div>
<div class="fld"><label>Repository</label><input id="cfgRepo" placeholder="xtralight-ceu-targets"></div>
<div class="fld"><label>Branch</label><input id="cfgBranch" value="main"></div>
<div class="fld"><label>Token</label><input id="cfgToken" type="password" placeholder="github_pat_&hellip;"></div>
<div class="fld"><label>&nbsp;</label><label style="text-transform:none;font-size:12px;font-weight:600">
<input type="checkbox" id="cfgRemember" style="width:auto"> Remember token on this device</label></div>
<div class="fld"><label>&nbsp;</label><button class="btn-blue" id="cfgSave">Save setup</button></div>
</div>
</div>

<div style="margin-top:18px">
<div style="font-weight:900;font-size:20px">CEU Lunch &amp; Learn Command Dashboard</div>
<div class="sub">Government-sector A/E &amp; MEP targets &middot; page built __DATE__ from data/targets.csv
&middot; open a firm to add field notes</div>
</div>

<div class="kpis" id="kpis"></div>

<h2>PIPELINE BY STATUS</h2>
<div class="funnel" id="funnel"></div>

<h2>TARGET FIRMS</h2>
<div class="controls">
<input id="q" type="search" placeholder="Search firm, city, notes&hellip;">
<select id="fstate"><option value="">All states</option></select>
<select id="ftier"><option value="">All tiers</option>
<option>Tier 1</option><option>Tier 2</option><option>Tier 3</option></select>
<select id="ffit"><option value="">All courses</option>
<option value="FED">FED (Federal Secure)</option><option value="COR">COR (Correctional)</option>
<option value="FED+COR">Both</option></select>
<select id="fstatus"><option value="">All statuses</option></select>
</div>
<div class="count" id="count"></div>
<table id="tbl">
<thead><tr>
<th data-k="state">STATE</th><th data-k="firm">FIRM</th>
<th data-k="city" class="hidemob">HQ CITY</th><th data-k="type" class="hidemob">TYPE</th>
<th data-k="fit">FIT</th><th data-k="tier">TIER</th><th data-k="status">STATUS</th>
<th data-k="rep" class="hidemob">REP AGENCY</th>
</tr></thead>
<tbody id="tb"></tbody>
</table>
<div class="note">Gold edge = unsent edits on this device. Edits save locally as you type and survive
refresh &mdash; hit <b>Commit changes</b> when you're back on signal to push them to the repo. The
workbook and this page rebuild automatically after each commit. Tier 1 firms in bold.</div>
</div>

<footer><div class="wrap"><div class="frow">
<div class="tag">Working Harder. Lighting Smarter.<sup>&reg;</sup></div>
<div class="co">XtraLight Manufacturing, Ltd. &nbsp;|&nbsp; 8812 Frey Road, Houston, TX 77034
&nbsp;|&nbsp; 800-678-6960 &nbsp;|&nbsp; xtralight.com</div>
</div></div></footer>

<script>
const DATA = __DATA__;
const STATUSES = ["Not Started","Outreach Sent","In Scheduling","Scheduled","Presented","Follow-Up","Declined","Dormant"];
const SB = {"Not Started":"b-grey","Outreach Sent":"b-blue","In Scheduling":"b-gold",
"Scheduled":"b-green","Presented":"b-dgreen","Follow-Up":"b-blue","Declined":"b-dim","Dormant":"b-dim"};
const IDX = {rep:10,status:11,course:12,office:13,contact:14,title:15,email:16,outreach:17,lldate:18,next:19,notes:20};
const EDITS = [
 ["status","Status","select",STATUSES],
 ["course","Course to book","select",["","FED","COR","Either"]],
 ["rep","Rep agency","text"],
 ["office","Target office / city","text"],
 ["contact","Contact name","text"],
 ["title","Contact title","text"],
 ["email","Email / phone","text"],
 ["outreach","Outreach date","text"],
 ["lldate","L&L date","text"],
 ["next","Next action","text"],
 ["notes","Notes","textarea"]
];
const LSK="ceu_drafts_v1", LSC="ceu_cfg_v1";
let drafts = {}; try{drafts = JSON.parse(localStorage.getItem(LSK)||"{}")}catch(e){}
let cfg = {owner:"",repo:"",branch:"main",remember:false}; let token="";
try{const s=JSON.parse(localStorage.getItem(LSC)||"{}");Object.assign(cfg,s);token=s.token||""}catch(e){}
let sortK="state", sortAsc=true;

const key = d => d.state+"||"+d.firm;
// apply saved drafts to in-memory data
DATA.forEach(d=>{const dr=drafts[key(d)]; if(dr) Object.assign(d,dr);});

function esc(s){return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}
function msg(t,cls){const m=document.getElementById("msg");m.textContent=t;m.className="msg "+(cls||"");}

function kpis(){
  const t=DATA.length, c=s=>DATA.filter(d=>d.status===s).length;
  const t1=DATA.filter(d=>d.tier==="Tier 1").length;
  const ns=c("Not Started"), sch=c("Scheduled"), pr=c("Presented");
  const act=c("Outreach Sent")+c("In Scheduling");
  const rate=(t-ns)>0?Math.round(100*(sch+pr)/(t-ns)):0;
  const items=[[t,"Total targets"],[t1,"Tier 1"],[ns,"Not started"],[act,"Active outreach"],
  [sch,"Scheduled"],[pr,"Presented"],[rate+"%","Booked rate"]];
  document.getElementById("kpis").innerHTML =
    items.map(i=>`<div class="kpi"><div class="n">${i[0]}</div><div class="l">${i[1]}</div></div>`).join("");
  const mx=Math.max(...STATUSES.map(s=>c(s)),1);
  document.getElementById("funnel").innerHTML = STATUSES.map(s=>{const n=c(s);
    return `<div class="row"><div class="lab">${s}</div>
    <div class="bar" style="width:${Math.max(2,Math.round(520*n/mx))}px"></div>
    <div class="ct">${n}</div></div>`;}).join("");
}

function filters(){
  const st=[...new Set(DATA.map(d=>d.state))].sort();
  document.getElementById("fstate").innerHTML += st.map(s=>`<option>${esc(s)}</option>`).join("");
  document.getElementById("fstatus").innerHTML += STATUSES.map(s=>`<option>${s}</option>`).join("");
}

function fieldHtml(d,f){
  const [id,label,kind,opts]=f, v=d[id]||"";
  if(kind==="select"){
    return `<div class="fld"><label>${label}</label>
    <select data-f="${id}">${opts.map(o=>`<option ${o===v?"selected":""}>${o}</option>`).join("")}</select></div>`;
  }
  if(kind==="textarea"){
    return `<div class="fld wide"><label>${label}</label>
    <textarea data-f="${id}">${esc(v)}</textarea></div>`;
  }
  return `<div class="fld"><label>${label}</label><input data-f="${id}" value="${esc(v)}"></div>`;
}

function rows(){
  const q=document.getElementById("q").value.toLowerCase();
  const fs=document.getElementById("fstate").value, ft=document.getElementById("ftier").value;
  const ff=document.getElementById("ffit").value, fu=document.getElementById("fstatus").value;
  let out=DATA.filter(d=>
    (!fs||d.state===fs)&&(!ft||d.tier===ft)&&(!ff||d.fit===ff)&&(!fu||d.status===fu)&&
    (!q||[d.firm,d.city,d.type,d.strengths,d.angle,d.notes,d.rep,d.office]
      .join(" ").toLowerCase().includes(q)));
  out.sort((a,b)=>{const va=(a[sortK]||"").toLowerCase(),vb=(b[sortK]||"").toLowerCase();
    return (va<vb?-1:va>vb?1:0)*(sortAsc?1:-1);});
  document.getElementById("count").textContent=out.length+" of "+DATA.length+" firms shown";
  const tierCls={"Tier 1":"tier1","Tier 2":"tier2","Tier 3":"tier3"};
  document.getElementById("tb").innerHTML = out.map(d=>{
    const k=key(d), ed=drafts[k]?" edited":"";
    const web = d.website && !d.website.includes("verify")
      ? `<a href="https://${esc(d.website)}" target="_blank" rel="noopener">${esc(d.website)}</a>`
      : esc(d.website);
    return `<tr class="main ${d.tier==="Tier 1"?"t1":""}${ed}" data-key="${esc(k)}">
    <td>${esc(d.state)}</td><td class="firm">${esc(d.firm)}</td>
    <td class="hidemob">${esc(d.city)}</td><td class="hidemob">${esc(d.type)}</td>
    <td>${esc(d.fit)}</td><td class="tierchip ${tierCls[d.tier]||""}">${esc(d.tier)}</td>
    <td><span class="badge ${SB[d.status]||"b-grey"}">${esc(d.status)}</span></td>
    <td class="hidemob">${esc(d.rep)}</td></tr>
    <tr class="detail" style="display:none" data-key="${esc(k)}"><td colspan="8">
    <div class="intel">
    <div><b>Website:</b> ${web}</div>
    <div><b>Sector strengths:</b> ${esc(d.strengths)}</div>
    <div><b>2025 standing:</b> ${esc(d.standing)}</div>
    <div><b>Angle:</b> ${esc(d.angle)}</div>
    </div>
    <div class="fnh">FIELD NOTES &mdash; edits save on this device as you type</div>
    <div class="form">${EDITS.map(f=>fieldHtml(d,f)).join("")}</div>
    </td></tr>`;}).join("");

  document.querySelectorAll("tr.main").forEach(tr=>{
    tr.addEventListener("click",()=>{const nx=tr.nextElementSibling;
      nx.style.display = nx.style.display==="none"?"":"none";});});
  document.querySelectorAll("tr.detail [data-f]").forEach(inp=>{
    const k=inp.closest("tr.detail").dataset.key;
    inp.addEventListener("input",()=>stage(k,inp.dataset.f,inp.value));
    inp.addEventListener("click",e=>e.stopPropagation());
  });
}

function stage(k,f,v){
  drafts[k]=drafts[k]||{}; drafts[k][f]=v;
  try{localStorage.setItem(LSK,JSON.stringify(drafts))}catch(e){}
  const d=DATA.find(x=>key(x)===k); if(d){d[f]=v;}
  const main=document.querySelector(`tr.main[data-key="${CSS.escape(k)}"]`);
  if(main){main.classList.add("edited");
    if(f==="status"){const cell=main.children[6];
      cell.innerHTML=`<span class="badge ${SB[v]||"b-grey"}">${esc(v)}</span>`;}
    if(f==="rep"){main.children[7].textContent=v;}}
  kpis(); updatePending();
}

function updatePending(){
  const n=Object.keys(drafts).length;
  const b=document.getElementById("commitBtn");
  b.disabled = n===0;
  b.textContent = n? `Commit ${n} firm${n>1?"s":""}` : "Commit changes";
  document.getElementById("discardBtn").style.display = n? "" : "none";
}

/* ---------- CSV (RFC 4180) ---------- */
function parseCSV(text){
  const rows=[[""]]; let r=0,c=0,inQ=false;
  for(let i=0;i<text.length;i++){const ch=text[i];
    if(inQ){ if(ch==='"'){ if(text[i+1]==='"'){rows[r][c]+='"';i++;} else inQ=false; }
      else rows[r][c]+=ch; }
    else{ if(ch==='"') inQ=true;
      else if(ch===','){rows[r].push("");c++;}
      else if(ch==='\n'){rows.push([""]);r++;c=0;}
      else if(ch!=='\r') rows[r][c]+=ch; } }
  if(rows.length&&rows[rows.length-1].length===1&&rows[rows.length-1][0]==="")rows.pop();
  return rows;
}
function csvCell(v){v=String(v??"");return /[",\n\r]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v;}
function serializeCSV(rows){return rows.map(r=>r.map(csvCell).join(",")).join("\r\n")+"\r\n";}

/* ---------- GitHub write-back ---------- */
function apiUrl(){return `https://api.github.com/repos/${cfg.owner}/${cfg.repo}/contents/data/targets.csv`;}
async function commit(){
  if(!cfg.owner||!cfg.repo||!token){msg("Setup needed: owner, repo, token.","err");
    document.getElementById("setup").style.display="block";return;}
  const b=document.getElementById("commitBtn"); b.disabled=true; msg("Fetching latest CSV\u2026");
  try{
    const H={Authorization:"Bearer "+token,Accept:"application/vnd.github+json"};
    const res=await fetch(apiUrl()+"?ref="+encodeURIComponent(cfg.branch),{headers:H});
    if(!res.ok)throw new Error("fetch "+res.status+(res.status===401?" (bad token?)":res.status===404?" (check owner/repo)":""));
    const j=await res.json();
    const bytes=Uint8Array.from(atob(j.content.replace(/\n/g,"")),ch=>ch.charCodeAt(0));
    const rows=parseCSV(new TextDecoder().decode(bytes));
    let applied=0, missing=[];
    for(const [k,fields] of Object.entries(drafts)){
      const [st,firm]=k.split("||");
      const row=rows.find((r,i)=>i>0&&r[0]===st&&r[1]===firm);
      if(!row){missing.push(firm);continue;}
      while(row.length<21)row.push("");
      for(const [f,v] of Object.entries(fields))row[IDX[f]]=v;
      applied++;
    }
    if(!applied)throw new Error("no matching rows in repo CSV");
    msg("Committing "+applied+" firm(s)\u2026");
    const out=serializeCSV(rows), enc=new TextEncoder().encode(out);
    let bin=""; for(let i=0;i<enc.length;i+=8192)bin+=String.fromCharCode.apply(null,enc.subarray(i,i+8192));
    const put=await fetch(apiUrl(),{method:"PUT",headers:{...H,"Content-Type":"application/json"},
      body:JSON.stringify({message:`Field notes: ${applied} firm(s) updated via dashboard`,
        content:btoa(bin),sha:j.sha,branch:cfg.branch})});
    if(put.status===409)throw new Error("conflict \u2014 repo changed mid-save; hit Commit again");
    if(!put.ok)throw new Error("commit "+put.status);
    drafts={}; try{localStorage.removeItem(LSK)}catch(e){}
    document.querySelectorAll("tr.main.edited").forEach(t=>t.classList.remove("edited"));
    updatePending();
    msg("Committed"+(missing.length?" ("+missing.length+" unmatched)":"")+
        ". Cloud rebuild running \u2014 ~1 min.","ok");
  }catch(e){msg("Failed: "+e.message,"err"); b.disabled=false; updatePending();}
}

/* ---------- setup panel ---------- */
function initSetup(){
  document.getElementById("cfgOwner").value=cfg.owner||"";
  document.getElementById("cfgRepo").value=cfg.repo||"";
  document.getElementById("cfgBranch").value=cfg.branch||"main";
  document.getElementById("cfgToken").value=token||"";
  document.getElementById("cfgRemember").checked=!!cfg.remember;
  document.getElementById("setupBtn").addEventListener("click",()=>{
    const s=document.getElementById("setup");
    s.style.display=s.style.display==="block"?"none":"block";});
  document.getElementById("cfgSave").addEventListener("click",()=>{
    cfg.owner=document.getElementById("cfgOwner").value.trim();
    cfg.repo=document.getElementById("cfgRepo").value.trim();
    cfg.branch=document.getElementById("cfgBranch").value.trim()||"main";
    cfg.remember=document.getElementById("cfgRemember").checked;
    token=document.getElementById("cfgToken").value.trim();
    const store={...cfg}; if(cfg.remember)store.token=token;
    try{localStorage.setItem(LSC,JSON.stringify(store))}catch(e){}
    document.getElementById("setup").style.display="none";
    msg("Setup saved.","ok");});
  document.getElementById("commitBtn").addEventListener("click",commit);
  document.getElementById("discardBtn").addEventListener("click",()=>{
    if(!confirm("Discard all unsent edits on this device?"))return;
    drafts={}; try{localStorage.removeItem(LSK)}catch(e){}
    location.reload();});
}

document.querySelectorAll("th").forEach(th=>th.addEventListener("click",()=>{
  const k=th.dataset.k; if(sortK===k){sortAsc=!sortAsc}else{sortK=k;sortAsc=true} rows();}));
["q","fstate","ftier","ffit","fstatus"].forEach(id=>
  document.getElementById(id).addEventListener("input",rows));
kpis(); filters(); rows(); initSetup(); updatePending();
if(Object.keys(drafts).length)msg(Object.keys(drafts).length+" unsent edit(s) restored on this device.");
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
            .replace("__DATE__", date.today().strftime("%B %d, %Y")))
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Built {OUT_PATH}: {len(rows)} firms, {os.path.getsize(OUT_PATH)//1024} KB")


if __name__ == "__main__":
    main()
