# Prospect OS — Outreach Engine (cloud edition)

The outreach system now lives inside **your** Firebase project
(`agent-dashboard-95a62`), running 24/7 with no laptop dependency. Everything
is namespaced `outreach_*` in Firestore, so it sits cleanly beside your
existing Prospect OS data. No third-party outreach vendor anywhere.

**What runs where:**

| Piece | Where | Job |
|---|---|---|
| Cloud Functions | your Firebase project | prepare drafts · dispatch (window+caps) · poll inbox · 7:30 ET daily brief |
| Firestore `outreach_*` | your Firebase project | contacts, sequences, queue, replies, meetings, log |
| `outreach.html` | your GitHub Pages repo | the whole UI — approve from your phone anywhere |
| Microsoft refresh token | `outreach_private/ms_token` | rules-locked; Admin SDK only; revocable in Entra in 30 s |

**Alerts:** a prospect's reply is a real email in your real inbox — that's
your instant notification, on every device you own. The Needs Response queue
and the 7:30 brief cover the rest.

---

## Deploy (one time, ~20 minutes)

### 0. Prerequisites
- Node 18+ on your Mac, then: `npm install -g firebase-tools && firebase login`
- **Blaze plan** on the Firebase project (console → Upgrade). Required for
  scheduled functions. At this volume the free-tier allowances cover usage;
  expect ~$0/month.

### 1. Deploy the functions
```bash
cd prospect-os-outreach
firebase use agent-dashboard-95a62
cd functions && npm install && cd ..
firebase deploy --only functions
```

### 2. Merge the security rules
Open your **existing** Firestore rules (console → Firestore → Rules, or your
local rules file). Paste the match blocks from `firestore.outreach.rules`
**inside** your existing `match /databases/{database}/documents { ... }`
block, then publish/deploy. Do not replace your file — rules deploys replace
the whole ruleset.

### 3. Enable Google sign-in
Console → Authentication → Sign-in method → enable **Google**. Under
Authorized domains, confirm your GitHub Pages domain
(`<username>.github.io`) is listed; add it if not.

### 4. Add the UI to Prospect OS
- Copy `web/outreach.html` into your Prospect OS repo (GitHub Pages root).
- Paste your Firebase web config into the marked block at the top of the
  `<script>` (console → Project settings → Your apps → Config).
- Add a nav link from your existing pages: `<a href="outreach.html">Outreach</a>`
- Commit and push.

### 5. First run (in the browser, in this order)
1. Open `outreach.html` → **Sign in with Google** (your account becomes owner)
2. Settings → **Seed defaults**
3. Settings → enter **Tenant ID** and **Client ID** from the Entra app
   registration (walkthrough below) → **Save settings**
4. Settings → **Connect mailbox** → follow the code prompt → done
5. Dashboard → **Import CSV** (your 126-firm roster)
6. Dashboard → **Enroll roster in ceu_intro**
7. Work the **Approval queue** — nothing sends without your OK

### Entra app registration (same 10 minutes as before)
1. entra.microsoft.com → Identity → Applications → App registrations → **New**
2. Name `Prospect OS Outreach` · this organizational directory only → Register
3. Copy **Application (client) ID** and **Directory (tenant) ID** → Settings page
4. Authentication → Advanced → **Allow public client flows: Yes** → Save
5. API permissions → Microsoft Graph → *Delegated* → `Mail.Send`,
   `Mail.ReadWrite`, `User.Read`

If the portal blocks you, send IT: *"I'd like a public-client app registration
named 'Prospect OS Outreach' with delegated Graph permissions Mail.Send,
Mail.ReadWrite, User.Read, public client flows enabled. Personal sales tool
sending as me from my own mailbox under my own login — no service account,
no client secret."*

---

## Day-to-day

Approve drafts and clear replies from any device — phone included. The 7:30
brief tells you what happened and what's waiting; Monday's edition adds
variant and touch-performance tables. Edit copy in Firestore
(`outreach_sequences/ceu_intro`) — next drafts pick it up automatically.
Updating the engine = `git pull` + `firebase deploy --only functions`.

## Guardrails (identical to the local build)

Daily caps (25 new / 60 total, editable in Settings) · 9:15–4:45 ET weekday
window · ±25 min jitter · follow-ups threaded into the original email ·
stop-on-reply · stop-on-bounce · out-of-office pushes 7 days instead of
killing the sequence · permanent suppression list · CAN-SPAM footer on every
send · missed windows never "made up".

## Notes

- The digest cron's timezone is fixed at deploy (`America/New_York` in
  `functions/index.js`); if you ever change the config timezone, change it
  there too and redeploy.
- Backups: Firestore is replicated and durable by default. For belt-and-
  suspenders, console → Firestore → enable Point-in-Time Recovery, or run
  `gcloud firestore export gs://<bucket>` on occasion.
- Kill switch: Entra portal → the app registration → revoke, or delete
  `outreach_private/ms_token` in the console. Sending stops immediately.
