#!/usr/bin/env python3
"""Generate index.html - a self-contained, XtraLight-branded dashboard of the
CEU L&L target pipeline - from data/targets.csv.

Usage:  python scripts/build_site.py
Output: index.html (repo root)

The page embeds the data and the logo, so it works anywhere: GitHub Pages,
opened locally from a download, or attached to an email.
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
        next(reader)  # header
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


TEMPLATE = """<!DOCTYPE html>
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
header{border-bottom:4px solid var(--blue);background:#fff}
.hrow{display:flex;align-items:center;justify-content:space-between;padding:18px 0;gap:16px;flex-wrap:wrap}
.hrow img{height:52px}
.htitle{text-align:right}
.htitle .t1{font-weight:800;font-size:11px;letter-spacing:.14em;color:var(--blue)}
.htitle .t2{font-weight:900;font-size:20px;color:#000}
.htitle .t3{font-size:11px;color:var(--grey)}
h2{font-size:13px;font-weight:800;letter-spacing:.12em;color:var(--blue);margin:26px 0 12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;margin-top:22px}
.kpi{background:var(--tint);border-radius:10px;padding:14px 16px}
.kpi .n{font-size:26px;font-weight:900;color:var(--blue)}
.kpi .l{font-size:10.5px;font-weight:700;color:var(--grey);letter-spacing:.06em;text-transform:uppercase}
.funnel .row{display:flex;align-items:center;gap:10px;margin:6px 0}
.funnel .lab{width:120px;font-size:12px;font-weight:600}
.funnel .bar{height:16px;border-radius:8px;background:var(--blue);min-width:2px}
.funnel .ct{font-size:12px;font-weight:700;color:var(--grey)}
.controls{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0 10px}
.controls input,.controls select{font-family:inherit;font-size:13px;padding:8px 10px;
border:1.5px solid var(--line);border-radius:8px;background:#fff}
.controls input{flex:1;min-width:200px}
.count{font-size:12px;color:var(--grey);margin:4px 0 8px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{background:var(--blue);color:#fff;text-align:left;padding:9px 10px;font-size:11px;
letter-spacing:.05em;position:sticky;top:0;cursor:pointer;user-select:none}
td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
tr.main:hover{background:var(--tint);cursor:pointer}
tr.t1 td.firm{font-weight:700}
.badge{display:inline-block;padding:2px 9px;border-radius:9px;font-size:10.5px;font-weight:700;white-space:nowrap}
.b-grey{background:#ECEDEE;color:#555}.b-blue{background:#DCEFFB;color:#075E92}
.b-gold{background:#F6ECC8;color:#7A6404}.b-green{background:#DDEFD2;color:#3D6B1D}
.b-dgreen{background:#5D9732;color:#fff}.b-dim{background:#F1F1F1;color:#999}
.tierchip{font-weight:800;font-size:11px}
.tier1{color:var(--blue)}.tier2{color:var(--gold)}.tier3{color:var(--grey)}
tr.detail td{background:#FAFBFC;font-size:12px;color:#333;padding:12px 16px;border-left:3px solid var(--blue)}
tr.detail .dg{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:8px 24px}
tr.detail b{color:#000}
a{color:var(--blue);text-decoration:none;font-weight:600}
footer{margin-top:36px;background:#000;color:#fff}
footer .frow{display:flex;justify-content:space-between;align-items:center;padding:16px 0;
flex-wrap:wrap;gap:8px;font-size:12px}
footer .tag{font-weight:700}
footer .co{color:#92B6C7}
.note{font-size:11px;color:var(--grey);font-style:italic;margin-top:8px}
@media(max-width:640px){.htitle{text-align:left}.hidemob{display:none}}
</style>
</head>
<body>
<header><div class="wrap"><div class="hrow">
<img src="data:image/png;base64,__LOGO__" alt="XtraLight LED Lighting Solutions">
<div class="htitle">
<div class="t1">AIA CES PROGRAM</div>
<div class="t2">CEU Lunch &amp; Learn Command Dashboard</div>
<div class="t3">Government-sector A/E &amp; MEP targets &middot; built __DATE__ from data/targets.csv</div>
</div>
</div></div></header>

<div class="wrap">
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
<div class="note">Click any row for sector strengths, entry angle, contacts, and working notes.
Tier 1 firms shown in bold. To change data, edit data/targets.csv and commit &mdash; this page and the
Excel workbook rebuild automatically.</div>
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
let sortK = "state", sortAsc = true;

function kpis(){
  const t = DATA.length;
  const c = s => DATA.filter(d=>d.status===s).length;
  const t1 = DATA.filter(d=>d.tier==="Tier 1").length;
  const ns = c("Not Started"), sch = c("Scheduled"), pr = c("Presented");
  const act = c("Outreach Sent")+c("In Scheduling");
  const rate = (t-ns)>0 ? Math.round(100*(sch+pr)/(t-ns)) : 0;
  const items=[[t,"Total targets"],[t1,"Tier 1"],[ns,"Not started"],[act,"Active outreach"],
  [sch,"Scheduled"],[pr,"Presented"],[rate+"%","Booked rate"]];
  document.getElementById("kpis").innerHTML =
    items.map(i=>`<div class="kpi"><div class="n">${i[0]}</div><div class="l">${i[1]}</div></div>`).join("");
  const mx = Math.max(...STATUSES.map(s=>c(s)),1);
  document.getElementById("funnel").innerHTML = STATUSES.map(s=>{
    const n=c(s);
    return `<div class="row"><div class="lab">${s}</div>
    <div class="bar" style="width:${Math.max(2,Math.round(560*n/mx))}px"></div>
    <div class="ct">${n}</div></div>`;}).join("");
}

function esc(s){return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}

function filters(){
  const st=[...new Set(DATA.map(d=>d.state))].sort();
  document.getElementById("fstate").innerHTML += st.map(s=>`<option>${esc(s)}</option>`).join("");
  document.getElementById("fstatus").innerHTML += STATUSES.map(s=>`<option>${s}</option>`).join("");
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
  document.getElementById("count").textContent =
    out.length+" of "+DATA.length+" firms shown";
  const tierCls={"Tier 1":"tier1","Tier 2":"tier2","Tier 3":"tier3"};
  document.getElementById("tb").innerHTML = out.map((d,i)=>{
    const web = d.website && !d.website.includes("verify")
      ? `<a href="https://${esc(d.website)}" target="_blank" rel="noopener">${esc(d.website)}</a>`
      : esc(d.website);
    return `<tr class="main ${d.tier==="Tier 1"?"t1":""}" data-i="${i}">
    <td>${esc(d.state)}</td><td class="firm">${esc(d.firm)}</td>
    <td class="hidemob">${esc(d.city)}</td><td class="hidemob">${esc(d.type)}</td>
    <td>${esc(d.fit)}</td><td class="tierchip ${tierCls[d.tier]||""}">${esc(d.tier)}</td>
    <td><span class="badge ${SB[d.status]||"b-grey"}">${esc(d.status)}</span></td>
    <td class="hidemob">${esc(d.rep)}</td></tr>
    <tr class="detail" style="display:none"><td colspan="8"><div class="dg">
    <div><b>Website:</b> ${web}</div>
    <div><b>Sector strengths:</b> ${esc(d.strengths)}</div>
    <div><b>2025 standing:</b> ${esc(d.standing)}</div>
    <div><b>Angle:</b> ${esc(d.angle)}</div>
    <div><b>Course to book:</b> ${esc(d.course)||"&mdash;"} &nbsp; <b>Target office:</b> ${esc(d.office)||"&mdash;"}</div>
    <div><b>Contact:</b> ${esc(d.contact)||"&mdash;"} ${esc(d.title)} ${esc(d.email)}</div>
    <div><b>Outreach:</b> ${esc(d.outreach)||"&mdash;"} &nbsp; <b>L&amp;L date:</b> ${esc(d.lldate)||"&mdash;"}</div>
    <div><b>Next action:</b> ${esc(d.next)||"&mdash;"}</div>
    <div><b>Notes:</b> ${esc(d.notes)||"&mdash;"}</div>
    </div></td></tr>`;}).join("");
  document.querySelectorAll("tr.main").forEach(tr=>{
    tr.addEventListener("click",()=>{const nx=tr.nextElementSibling;
      nx.style.display = nx.style.display==="none"?"":"none";});});
}

document.querySelectorAll("th").forEach(th=>th.addEventListener("click",()=>{
  const k=th.dataset.k; if(sortK===k){sortAsc=!sortAsc}else{sortK=k;sortAsc=true} rows();}));
["q","fstate","ftier","ffit","fstatus"].forEach(id=>
  document.getElementById(id).addEventListener("input",rows));
kpis(); filters(); rows();
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
