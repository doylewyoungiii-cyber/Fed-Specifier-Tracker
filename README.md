# XtraLight CEU Lunch & Learn — Target Pipeline

Government-sector A/E and MEP firm targets for XtraLight's AIA CES lunch-and-learn program
(Federal Secure Facilities + Correctional/Secure Environments HSW courses).

**Source of truth:** `data/targets.csv` (126 firms, 21 columns).
**Deliverable:** `output/XtraLight_CEU_LL_Command_Workbook.xlsx` — generated, never hand-edited as the master.
Every roster change is a readable diff in Git; the workbook is rebuilt from the CSV on demand.

## How it works

```
data/targets.csv  ──►  scripts/build_workbook.py  ──►  output/…Command_Workbook.xlsx
      ▲                                                        │
      └────────────  scripts/sync_from_workbook.py  ◄──────────┘
```

The GitHub Action (`.github/workflows/build.yml`) runs the build automatically on every
commit that touches `data/` or `scripts/`, then commits the fresh workbook back to `output/`.

## One-time GitHub setup

1. Create a **private** repo at github.com/new (this file contains sales strategy — keep it private).
2. Push this folder:
   ```bash
   cd xtralight-ceu-targets
   git init && git add -A && git commit -m "initial: CEU target pipeline"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/xtralight-ceu-targets.git
   git push -u origin main
   ```
   *No git installed?* On github.com, create the repo, then **Add file → Upload files** and drag the
   folder contents in. Upload `data/`, `scripts/`, `.github/`, `README.md`, `requirements.txt`,
   `.gitignore` — keep the folder structure.
3. Check **Settings → Actions → General → Workflow permissions** = "Read and write permissions."
   (The Action needs this to commit the rebuilt workbook.)

## Editing on the fly — two workflows, pick ONE per session

**A. Browser / phone (quick status changes):**
1. Open `data/targets.csv` on github.com → pencil icon.
2. Edit (it's raw text — fine for changing a status word or a note, clumsy for bulk edits).
3. Commit. ~60 seconds later the Action commits a rebuilt workbook to `output/`. Download it there.

**B. Excel (real working sessions):**
1. Pull/download the workbook, work the Targets tab in Excel (dropdowns, contacts, dates, notes).
2. `python scripts/sync_from_workbook.py path/to/your-edited.xlsx` — pulls your edits back into the CSV.
3. Commit both files.

**The rule that keeps this alive:** never edit the CSV and the workbook in parallel. One surface
at a time, sync, commit. Two sources of truth = dead dashboard.

## Local build

```bash
pip install -r requirements.txt
python scripts/build_workbook.py
```

## CSV columns

| Cols | Content | Who touches it |
|---|---|---|
| A–J | State, Firm, HQ City, Type, Website, Sector Strengths, 2025 Standing, CEU Fit (FED/COR/FED+COR), Priority (Tier 1–3), Angle/Entry Notes | Edit when roster facts change; append rows to add firms |
| K–U | Rep Agency, Status, Course to Book, Target Office, Contact Name/Title/Email, Outreach Date, L&L Date, Next Action, Notes | Working pipeline data — yours |

Status values (must match exactly for the dashboard to count them):
`Not Started, Outreach Sent, In Scheduling, Scheduled, Presented, Follow-Up, Declined, Dormant`

## Provenance

Rankings from BD+C 2025 Giants 400 Report (published Jan–Feb 2026) plus established
federal/justice/VA practices from public firm information, compiled July 2026.
Rows marked `(verify ...)` need confirmation before outreach.
