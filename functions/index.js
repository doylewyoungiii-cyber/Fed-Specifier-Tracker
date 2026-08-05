/**
 * Prospect OS — Outreach Engine (Cloud Functions, Node 20)
 *
 * The full engine, ported from the local build, running 24/7 inside YOUR
 * Firebase project. Nothing here talks to any third-party outreach vendor.
 *
 * Scheduled jobs:
 *   prepareDrafts  every 10 min — creates drafts for due touches (approval queue)
 *   dispatchSends  every 5 min  — sends approved emails (window + caps enforced)
 *   pollInbox      every 5 min  — matches replies, halts sequences
 *   dailyDigest    07:30 ET     — emails you the brief (Mondays add weekly stats)
 *
 * Callables (used by web/outreach.html, owner-only):
 *   seedDefaults, importContacts, enrollAll, msAuthStart, msAuthPoll
 *
 * Mailbox credentials: a Microsoft refresh token stored in
 * outreach_private/ms_token — locked to Admin-SDK-only by security rules,
 * rotated automatically, revocable any time from the Entra portal.
 *
 * Guardrails (hard-coded philosophy, values in outreach_settings/config):
 *   daily caps · business-hours window · timing jitter · stop-on-reply ·
 *   stop-on-bounce · permanent suppression · CAN-SPAM footer on every send ·
 *   missed windows are never "made up".
 */
"use strict";

const { onSchedule } = require("firebase-functions/v2/scheduler");
const { onCall, HttpsError } = require("firebase-functions/v2/https");
const { setGlobalOptions } = require("firebase-functions/v2");
const admin = require("firebase-admin");

admin.initializeApp();
const db = admin.firestore();
const FieldValue = admin.firestore.FieldValue;
const Timestamp = admin.firestore.Timestamp;

setGlobalOptions({ region: "us-central1", maxInstances: 3 });

/* ----------------------------- config ----------------------------------- */

const DEFAULT_CONFIG = {
  mailbox: "doyle@xlm.com",
  displayName: "Doyle W. Young III",
  tenantId: "",
  clientId: "",
  timezone: "America/New_York",
  sendWindow: { start: "09:15", end: "16:45", days: ["Mon", "Tue", "Wed", "Thu", "Fri"] },
  dailyNewContactCap: 25,
  dailyTotalSendCap: 60,
  jitterMinutes: 25,
  approvalMode: true,
  collateralLink: "https://xtralight.com/ceu",
  physicalAddress: "XtraLight Manufacturing, Ltd. \u00b7 8812 Frey Road, Houston, TX 77034",
  optOutLine: "If this isn't relevant to your practice, just reply \"no thanks\" and I won't follow up again.",
  digestEnabled: true,
  sessionGoal: 12,
  ownerUid: null,
  ownerEmail: null,
};

const DEFAULT_SEQUENCE = {
  variants: ["A", "B"],
  touches: [
    {
      day: 0,
      subject: {
        A: "HSW credits for {firm} \u2014 lunch on us",
        B: "AIA CES lunch-and-learn for your {city} team",
      },
      body:
        "<p>{first_name},</p>" +
        "<p>I run channel sales for XtraLight, and we just launched three AIA " +
        "CES\u2013registered HSW courses I think would land well with your team \u2014 " +
        "federal secure facilities, correctional/secure environments, and food " +
        "&amp; beverage processing. Real spec-level content, not a product pitch " +
        "with a course number stapled to it.</p>" +
        "<p>We deliver them as a one-hour lunch-and-learn at your office or " +
        "virtually, and we handle lunch. Would a session make sense for {firm} " +
        "in the next few weeks?</p><p>Doyle</p>",
    },
    {
      day: 4,
      subject: { A: "", B: "" },
      body:
        "<p>{first_name} \u2014 floating this back to the top of your inbox. Happy to " +
        "send the one-page course descriptions if that's easier to route to " +
        "whoever coordinates CEU sessions at {firm}.</p><p>Doyle</p>",
    },
    {
      day: 10,
      subject: { A: "", B: "" },
      body:
        "<p>{first_name}, one more useful piece: the course most firms grab first " +
        "covers where security requirements and life-safety lighting collide in " +
        "federal and secure facilities \u2014 a gap that shows up in specs constantly. " +
        "Course outlines here: {collateral_link}</p>" +
        "<p>If there's a better person at {firm} to coordinate with, point me " +
        "their way and I'll take it from there.</p><p>Doyle</p>",
    },
    {
      day: 18,
      subject: { A: "", B: "" },
      body:
        "<p>{first_name} \u2014 I'll close the loop here rather than keep nudging. If " +
        "HSW credits over lunch become useful this fall, my door's open. Either " +
        "way, I appreciate the inbox space.</p><p>Doyle</p>",
    },
  ],
};

async function getConfig() {
  const snap = await db.doc("outreach_settings/config").get();
  if (!snap.exists) return null;
  return { ...DEFAULT_CONFIG, ...snap.data() };
}

async function logEvent(kind, detail) {
  await db.collection("outreach_log").add({
    ts: FieldValue.serverTimestamp(), kind, detail: String(detail).slice(0, 500),
  });
}

/* ------------------------- timezone / window math ------------------------ */

function tzParts(tz, date) {
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: tz, weekday: "short", year: "numeric", month: "2-digit",
    day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit",
    hour12: false,
  });
  const out = {};
  for (const p of fmt.formatToParts(date)) out[p.type] = p.value;
  if (out.hour === "24") out.hour = "00";
  return out;
}

function tzOffsetMs(tz, date) {
  const p = tzParts(tz, date);
  const asUtc = Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute, +p.second);
  return asUtc - date.getTime();
}

/** UTC instant of a wall-clock time in tz (one DST correction pass). */
function localToUtc(tz, y, mo, d, hh, mm) {
  let guess = new Date(Date.UTC(y, mo - 1, d, hh, mm));
  guess = new Date(guess.getTime() - tzOffsetMs(tz, guess));
  const p = tzParts(tz, guess);
  const drift = (hh - +p.hour) * 60 + (mm - +p.minute);
  if (drift !== 0) guess = new Date(guess.getTime() + drift * 60000);
  return guess;
}

function inSendWindow(cfg, when = new Date()) {
  const p = tzParts(cfg.timezone, when);
  if (!cfg.sendWindow.days.includes(p.weekday)) return false;
  const cur = +p.hour * 60 + +p.minute;
  const [sh, sm] = cfg.sendWindow.start.split(":").map(Number);
  const [eh, em] = cfg.sendWindow.end.split(":").map(Number);
  return cur >= sh * 60 + sm && cur <= eh * 60 + em;
}

function nextWindowOpen(cfg, after) {
  const [sh, sm] = cfg.sendWindow.start.split(":").map(Number);
  const [eh, em] = cfg.sendWindow.end.split(":").map(Number);
  for (let d = 0; d < 21; d++) {
    const probe = new Date(after.getTime() + d * 86400000);
    const p = tzParts(cfg.timezone, probe);
    if (!cfg.sendWindow.days.includes(p.weekday)) continue;
    const startUtc = localToUtc(cfg.timezone, +p.year, +p.month, +p.day, sh, sm);
    const endUtc = localToUtc(cfg.timezone, +p.year, +p.month, +p.day, eh, em);
    if (after.getTime() <= endUtc.getTime()) {
      return after.getTime() > startUtc.getTime() ? after : startUtc;
    }
  }
  throw new Error("No open send window in the next 3 weeks \u2014 check settings.");
}

function jitterMs(cfg) {
  const j = (cfg.jitterMinutes || 20) * 60000;
  return (Math.random() * 2 - 1) * j;
}

function localDateKey(cfg, when = new Date()) {
  const p = tzParts(cfg.timezone, when);
  return `${p.year}-${p.month}-${p.day}`;
}

/* --------------------------- template rendering -------------------------- */

function renderTemplate(str, values) {
  return String(str || "").replace(/\{(\w+)\}/g, (_, k) =>
    values[k] === undefined || values[k] === null ? "" : String(values[k]));
}

function footer(cfg) {
  return (
    '<p style="color:#6b7280;font-size:12px;margin-top:28px">' +
    cfg.optOutLine + "<br>" + cfg.physicalAddress + "</p>"
  );
}

/* -------------------------- reply classification ------------------------- */

const OOO_RX = /automatic reply|out of (the )?office|auto[- ]?reply|on leave|on vacation|parental leave|away from/i;
const BOUNCE_FROM_RX = /postmaster|mailer-daemon|microsoftexchange/i;
const BOUNCE_SUBJ_RX = /undeliverable|delivery has failed|delivery status/i;
const OPT_OUT_RX = /\bunsubscribe\b|\bremove me\b|\bstop emailing\b|\btake me off\b|\bopt out\b|\bno thanks\b|\bdo not contact\b/i;

function classify(fromEmail, subject, preview) {
  const text = `${subject || ""} ${preview || ""}`;
  if (BOUNCE_FROM_RX.test(fromEmail || "") || BOUNCE_SUBJ_RX.test(subject || "")) return "bounce";
  if (OOO_RX.test(text)) return "out_of_office";
  if (OPT_OUT_RX.test(text)) return "opt_out";
  return "replied";
}

/* ------------------------------ Microsoft Graph -------------------------- */

const GRAPH = "https://graph.microsoft.com/v1.0";
const MS_SCOPES =
  "https://graph.microsoft.com/Mail.Send https://graph.microsoft.com/Mail.ReadWrite offline_access";

async function getAccessToken(cfg) {
  const ref = db.doc("outreach_private/ms_token");
  const snap = await ref.get();
  if (!snap.exists) {
    throw new Error("Mailbox not connected \u2014 use Connect mailbox in Settings.");
  }
  const { refreshToken } = snap.data();
  const body = new URLSearchParams({
    client_id: cfg.clientId,
    grant_type: "refresh_token",
    refresh_token: refreshToken,
    scope: MS_SCOPES,
  });
  const r = await fetch(
    `https://login.microsoftonline.com/${cfg.tenantId}/oauth2/v2.0/token`,
    { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body },
  );
  const j = await r.json();
  if (!j.access_token) {
    throw new Error("Token refresh failed: " + JSON.stringify(j).slice(0, 300));
  }
  if (j.refresh_token && j.refresh_token !== refreshToken) {
    await ref.set(
      { refreshToken: j.refresh_token, rotatedAt: FieldValue.serverTimestamp() },
      { merge: true },
    );
  }
  return j.access_token;
}

async function graphFetch(cfg, path, options = {}) {
  const token = await getAccessToken(cfg);
  const r = await fetch(path.startsWith("http") ? path : GRAPH + path, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  if (!r.ok) throw new Error(`Graph ${r.status}: ${(await r.text()).slice(0, 400)}`);
  return r.status === 204 || r.status === 202 ? null : r.json();
}

/** New thread. Returns { msgId, conversationId }. */
async function sendNew(cfg, toEmail, toName, subject, bodyHtml) {
  const draft = await graphFetch(cfg, "/me/messages", {
    method: "POST",
    body: JSON.stringify({
      subject,
      body: { contentType: "HTML", content: bodyHtml },
      toRecipients: [{ emailAddress: { address: toEmail, name: toName || toEmail } }],
    }),
  });
  await graphFetch(cfg, `/me/messages/${draft.id}/send`, { method: "POST" });
  return { msgId: draft.id, conversationId: draft.conversationId };
}

/** Follow-up inside an existing thread. Graph won't accept custom In-Reply-To
 * headers, so: createReplyAll off our own most recent sent message (preserves
 * threading), force recipients to the prospect, replace the body, send. */
async function sendFollowup(cfg, conversationId, toEmail, bodyHtml) {
  const q =
    "/me/mailFolders/sentitems/messages" +
    `?$filter=conversationId eq '${conversationId}'` +
    "&$orderby=sentDateTime desc&$top=1&$select=id";
  const found = await graphFetch(cfg, q);
  if (!found.value || !found.value.length) {
    throw new Error(`No sent anchor for conversation ${conversationId}`);
  }
  const reply = await graphFetch(
    cfg, `/me/messages/${found.value[0].id}/createReplyAll`,
    { method: "POST", body: JSON.stringify({}) },
  );
  await graphFetch(cfg, `/me/messages/${reply.id}`, {
    method: "PATCH",
    body: JSON.stringify({
      body: { contentType: "HTML", content: bodyHtml },
      toRecipients: [{ emailAddress: { address: toEmail } }],
      ccRecipients: [],
    }),
  });
  await graphFetch(cfg, `/me/messages/${reply.id}/send`, { method: "POST" });
  return reply.id;
}

async function inboxSince(cfg, isoUtc) {
  let url =
    "/me/mailFolders/inbox/messages" +
    `?$filter=receivedDateTime ge ${isoUtc}` +
    "&$orderby=receivedDateTime asc&$top=50" +
    "&$select=id,conversationId,from,subject,bodyPreview,receivedDateTime";
  const out = [];
  while (url) {
    const j = await graphFetch(cfg, url);
    out.push(...(j.value || []));
    url = j["@odata.nextLink"] || null;
  }
  return out;
}

/* --------------------------- enrollment advance -------------------------- */

async function advanceEnrollment(cfg, enrollRef, seq, touchJustHandled) {
  if (touchJustHandled >= seq.touches.length) {
    await enrollRef.update({
      currentTouch: touchJustHandled, status: "completed",
      nextSendAt: null, draftForTouch: FieldValue.delete(),
    });
    return;
  }
  const offsetDays =
    seq.touches[touchJustHandled].day - seq.touches[touchJustHandled - 1].day;
  let next = new Date(Date.now() + offsetDays * 86400000 + jitterMs(cfg));
  next = nextWindowOpen(cfg, next);
  await enrollRef.update({
    currentTouch: touchJustHandled,
    nextSendAt: Timestamp.fromDate(next),
    draftForTouch: FieldValue.delete(),
  });
}

/* ============================ SCHEDULED JOBS ============================= */

exports.prepareDrafts = onSchedule(
  { schedule: "every 10 minutes", maxInstances: 1 },
  async () => {
    const cfg = await getConfig();
    if (!cfg) return;
    const now = Timestamp.now();
    const active = await db.collection("outreach_enrollments")
      .where("status", "==", "active").get();
    let created = 0;

    for (const doc of active.docs) {
      const e = doc.data();
      if (!e.nextSendAt || e.nextSendAt.toMillis() > now.toMillis()) continue;
      const nextTouch = (e.currentTouch || 0) + 1;
      if (e.draftForTouch === nextTouch) continue; // draft already exists

      const contactSnap = await db.doc(`outreach_contacts/${e.contactId}`).get();
      if (!contactSnap.exists) continue;
      const c = contactSnap.data();

      const supp = await db.doc(`outreach_suppression/${c.email.toLowerCase()}`).get();
      if (supp.exists) {
        await doc.ref.update({ status: "opted_out", nextSendAt: null });
        continue;
      }

      const seqSnap = await db.doc(`outreach_sequences/${e.sequence}`).get();
      if (!seqSnap.exists) continue;
      const seq = seqSnap.data();
      if (nextTouch > seq.touches.length) {
        await doc.ref.update({ status: "completed", nextSendAt: null });
        continue;
      }

      const touch = seq.touches[nextTouch - 1];
      const values = {
        first_name: c.firstName, last_name: c.lastName, firm: c.firm,
        role: c.role, city: c.city, state: c.state,
        collateral_link: cfg.collateralLink,
      };
      const subjRaw = touch.subject
        ? (touch.subject[e.variant] ?? touch.subject.A ?? "")
        : "";
      await db.collection("outreach_sends").add({
        enrollmentId: doc.id, touch: nextTouch,
        subject: renderTemplate(subjRaw, values),
        bodyHtml: renderTemplate(touch.body, values) + footer(cfg),
        status: cfg.approvalMode ? "draft" : "approved",
        contactEmail: c.email, contactName: `${c.firstName} ${c.lastName}`.trim(),
        firm: c.firm || "", variant: e.variant,
        createdAt: FieldValue.serverTimestamp(),
      });
      await doc.ref.update({ draftForTouch: nextTouch });
      created++;
    }
    if (created) await logEvent("prepare", `${created} draft(s) created`);
  },
);

exports.dispatchSends = onSchedule(
  { schedule: "every 5 minutes", maxInstances: 1 }, // single instance: no double-sends
  async () => {
    const cfg = await getConfig();
    if (!cfg) return;

    const pending = await db.collection("outreach_sends")
      .where("status", "in", ["approved", "skipped"]).get();
    if (pending.empty) return;

    const counterRef = db.doc(`outreach_counters/${localDateKey(cfg)}`);
    const counterSnap = await counterRef.get();
    let { total = 0, firsts = 0 } = counterSnap.exists ? counterSnap.data() : {};

    // Skips process regardless of window (no email involved); sends need the window.
    const windowOpen = inSendWindow(cfg);
    const docs = pending.docs
      .map((d) => ({ ref: d.ref, ...d.data() }))
      .sort((a, b) => b.touch - a.touch); // follow-ups before fresh sends
    let sent = 0;

    for (const s of docs) {
      const enrollRef = db.doc(`outreach_enrollments/${s.enrollmentId}`);
      const enrollSnap = await enrollRef.get();
      if (!enrollSnap.exists) continue;
      const e = enrollSnap.data();
      const seqSnap = await db.doc(`outreach_sequences/${e.sequence}`).get();
      const seq = seqSnap.data();

      if (s.status === "skipped") {
        await s.ref.update({ status: "skipped_done" });
        if (e.status === "active") await advanceEnrollment(cfg, enrollRef, seq, s.touch);
        continue;
      }

      // status === 'approved'
      if (!windowOpen) continue;
      if (e.status !== "active") {
        await s.ref.update({ status: "skipped_done", error: "enrollment no longer active" });
        continue;
      }
      if (total >= cfg.dailyTotalSendCap) break;
      if (s.touch === 1 && firsts >= cfg.dailyNewContactCap) continue;

      const supp = await db.doc(`outreach_suppression/${s.contactEmail.toLowerCase()}`).get();
      if (supp.exists) {
        await s.ref.update({ status: "skipped_done", error: "suppressed" });
        continue;
      }

      await s.ref.update({ status: "sending" }); // crash-visibility marker
      try {
        let msgId;
        if (s.touch === 1 || !e.conversationId) {
          const res = await sendNew(cfg, s.contactEmail, s.contactName, s.subject, s.bodyHtml);
          msgId = res.msgId;
          await enrollRef.update({ conversationId: res.conversationId });
        } else {
          msgId = await sendFollowup(cfg, e.conversationId, s.contactEmail, s.bodyHtml);
        }
        await s.ref.update({
          status: "sent", graphMsgId: msgId, sentAt: FieldValue.serverTimestamp(),
        });
        await advanceEnrollment(cfg, enrollRef, seq, s.touch);
        total++; sent++;
        if (s.touch === 1) firsts++;
        await counterRef.set({ total, firsts }, { merge: true });
        await logEvent("sent", `${s.contactEmail} \u00b7 touch ${s.touch}`);
      } catch (err) {
        await s.ref.update({ status: "failed", error: String(err).slice(0, 400) });
        await logEvent("send_failed", `${s.contactEmail} touch ${s.touch}: ${err}`);
      }
    }
  },
);

exports.pollInbox = onSchedule(
  { schedule: "every 5 minutes", maxInstances: 1 },
  async () => {
    const cfg = await getConfig();
    if (!cfg) return;
    const stateRef = db.doc("outreach_private/state");
    const state = await stateRef.get();
    if (!state.exists || !state.data().lastPollUtc) {
      await stateRef.set(
        { lastPollUtc: new Date().toISOString().replace(/\.\d+Z$/, "Z") },
        { merge: true },
      );
      return;
    }
    let newest = state.data().lastPollUtc;
    let messages;
    try {
      messages = await inboxSince(cfg, newest);
    } catch (err) {
      await logEvent("error", `poll: ${err}`);
      return;
    }

    for (const m of messages) {
      if (m.receivedDateTime > newest) newest = m.receivedDateTime;
      if (!m.conversationId) continue;
      const match = await db.collection("outreach_enrollments")
        .where("conversationId", "==", m.conversationId).limit(1).get();
      if (match.empty) continue;
      const enrollDoc = match.docs[0];
      const e = enrollDoc.data();

      const fromEmail =
        ((m.from || {}).emailAddress || {}).address || "";
      const cls = classify(fromEmail, m.subject, m.bodyPreview);

      const replyRef = db.doc(`outreach_replies/${m.id.replace(/\//g, "_")}`);
      try {
        await replyRef.create({
          enrollmentId: enrollDoc.id, fromEmail,
          subject: m.subject || "", preview: (m.bodyPreview || "").slice(0, 300),
          classification: cls, touchAtReply: e.currentTouch || 0,
          contactName: e.contactName || "", firm: e.firm || "",
          receivedAt: m.receivedDateTime, handled: false,
          createdAt: FieldValue.serverTimestamp(),
        });
      } catch (_) {
        continue; // already recorded
      }

      const contactSnap = await db.doc(`outreach_contacts/${e.contactId}`).get();
      const email = contactSnap.exists ? contactSnap.data().email : fromEmail;

      if (cls === "out_of_office") {
        if (e.nextSendAt) {
          await enrollDoc.ref.update({
            nextSendAt: Timestamp.fromMillis(e.nextSendAt.toMillis() + 7 * 86400000),
          });
        }
        await logEvent("ooo", `${email} \u2014 pushed 7 days`);
      } else if (cls === "bounce") {
        await enrollDoc.ref.update({ status: "bounced", nextSendAt: null });
        await db.doc(`outreach_suppression/${email.toLowerCase()}`)
          .set({ reason: "hard bounce", addedAt: FieldValue.serverTimestamp() });
      } else if (cls === "opt_out") {
        await enrollDoc.ref.update({ status: "opted_out", nextSendAt: null });
        await db.doc(`outreach_suppression/${email.toLowerCase()}`)
          .set({ reason: "requested opt-out", addedAt: FieldValue.serverTimestamp() });
      } else {
        await enrollDoc.ref.update({ status: "replied", nextSendAt: null });
        await logEvent("reply", `${email} after touch ${e.currentTouch || 0}`);
      }
    }
    await stateRef.set({ lastPollUtc: newest }, { merge: true });
  },
);

/* ------------------------------- digest ---------------------------------- */
// NOTE: cron timezone is fixed at deploy time. If cfg.timezone ever changes,
// update timeZone below and redeploy.

exports.dailyDigest = onSchedule(
  { schedule: "30 7 * * *", timeZone: "America/New_York", maxInstances: 1 },
  async () => {
    const cfg = await getConfig();
    if (!cfg || !cfg.digestEnabled) return;

    const count = async (q) => (await q.count().get()).data().count;
    const queue = await count(db.collection("outreach_sends").where("status", "==", "draft"));
    const needs = await count(db.collection("outreach_replies")
      .where("classification", "==", "replied").where("handled", "==", false));
    const failed = await count(db.collection("outreach_sends").where("status", "==", "failed"));
    const active = await count(db.collection("outreach_enrollments").where("status", "==", "active"));
    const booked = await count(db.collection("outreach_meetings"));

    const yKey = localDateKey(cfg, new Date(Date.now() - 86400000));
    const ySnap = await db.doc(`outreach_counters/${yKey}`).get();
    const yesterday = ySnap.exists ? ySnap.data() : { total: 0, firsts: 0 };

    const since = new Date(Date.now() - 86400000).toISOString();
    const repliesSnap = await db.collection("outreach_replies")
      .where("receivedAt", ">=", since).get();
    const replies24 = repliesSnap.docs
      .filter((d) => d.data().classification === "replied").length;

    const bits = [];
    if (queue) bits.push(`${queue} draft(s) awaiting your approval`);
    if (needs) bits.push(`${needs} prospect repl(ies) need a response`);
    if (failed) bits.push(`${failed} send(s) failed \u2014 check the log`);
    const action = bits.length ? bits.join(" \u00b7 ") : "Nothing waiting on you.";

    const row = (l, v) =>
      `<tr><td style="padding:4px 14px 4px 0;color:#6f6d66">${l}</td>` +
      `<td style="padding:4px 0;font-family:Menlo,monospace"><b>${v}</b></td></tr>`;

    const weekly = tzParts(cfg.timezone, new Date()).weekday === "Mon";
    let html =
      '<div style="font:14px/1.6 -apple-system,Helvetica,Arial,sans-serif;color:#16211c;max-width:560px">' +
      `<p style="font-size:15px"><b>Your move:</b> ${action}</p>` +
      '<table style="border-collapse:collapse">' +
      row("Sent yesterday", yesterday.total || 0) +
      row("New contacts yesterday", yesterday.firsts || 0) +
      row("Replies (24h)", replies24) +
      row("Active in sequence", active) +
      row("Sessions booked vs goal", `${booked} / ${cfg.sessionGoal}`) +
      "</table>";

    if (weekly) {
      const enrolls = await db.collection("outreach_enrollments").get();
      const stats = {};
      for (const d of enrolls.docs) {
        const e = d.data();
        if (!(e.currentTouch > 0)) continue;
        const v = (stats[e.variant] ||= { n: 0, r: 0 });
        v.n++;
        if (e.status === "replied") v.r++;
      }
      const rows = Object.entries(stats).map(([v, s]) =>
        `<tr><td style="padding:2px 14px 2px 0">${v}</td>` +
        `<td style="padding:2px 14px 2px 0">${s.n}</td>` +
        `<td style="font-family:Menlo,monospace">${s.n ? (100 * s.r / s.n).toFixed(1) : 0}%</td></tr>`).join("");
      html +=
        '<p style="margin-top:18px"><b>Weekly optimization</b></p>' +
        '<table style="border-collapse:collapse"><tr>' +
        '<td style="padding:2px 14px 2px 0;color:#6f6d66">Variant</td>' +
        '<td style="padding:2px 14px 2px 0;color:#6f6d66">Touched</td>' +
        '<td style="color:#6f6d66">Reply rate</td></tr>' + rows + "</table>";
    }
    html +=
      '<p style="color:#9a988f;font-size:12px;margin-top:20px">Prospect OS ' +
      "\u00b7 outreach engine \u00b7 automated brief</p></div>";

    const p = tzParts(cfg.timezone, new Date());
    const subject =
      `Prospect OS ${weekly ? "Monday" : "daily"} brief \u2014 ${p.weekday} ${+p.month}/${+p.day}`;
    try {
      await sendNew(cfg, cfg.mailbox, cfg.displayName, subject, html);
      await logEvent("digest", subject);
    } catch (err) {
      await logEvent("error", `digest: ${err}`);
    }
  },
);

/* ============================== CALLABLES ================================ */

async function requireOwner(request) {
  if (!request.auth) throw new HttpsError("unauthenticated", "Sign in first.");
  const cfg = await getConfig();
  if (!cfg || !cfg.ownerUid) {
    throw new HttpsError("failed-precondition", "Run Seed defaults first.");
  }
  if (request.auth.uid !== cfg.ownerUid) {
    throw new HttpsError("permission-denied", "This system belongs to its owner.");
  }
  return cfg;
}

exports.seedDefaults = onCall(async (request) => {
  if (!request.auth) throw new HttpsError("unauthenticated", "Sign in first.");
  const cfgRef = db.doc("outreach_settings/config");
  const snap = await cfgRef.get();
  if (snap.exists && snap.data().ownerUid &&
      snap.data().ownerUid !== request.auth.uid) {
    throw new HttpsError("permission-denied", "Already owned by another account.");
  }
  await cfgRef.set({
    ...DEFAULT_CONFIG,
    ...(snap.exists ? snap.data() : {}),
    ownerUid: request.auth.uid,
    ownerEmail: request.auth.token.email || null,
  }, { merge: true });
  const seqRef = db.doc("outreach_sequences/ceu_intro");
  if (!(await seqRef.get()).exists) await seqRef.set(DEFAULT_SEQUENCE);
  await logEvent("seed", `owner ${request.auth.token.email || request.auth.uid}`);
  return { ok: true };
});

exports.importContacts = onCall(async (request) => {
  await requireOwner(request);
  const rows = request.data.rows || [];
  let added = 0, duplicates = 0, suppressed = 0, invalid = 0;
  for (const r of rows.slice(0, 1000)) {
    const email = String(r.email || "").trim().toLowerCase();
    if (!email.includes("@")) { invalid++; continue; }
    if ((await db.doc(`outreach_suppression/${email}`).get()).exists) { suppressed++; continue; }
    const dupe = await db.collection("outreach_contacts")
      .where("email", "==", email).limit(1).get();
    if (!dupe.empty) { duplicates++; continue; }
    await db.collection("outreach_contacts").add({
      email,
      firstName: String(r.first_name || r.firstName || "").trim(),
      lastName: String(r.last_name || r.lastName || "").trim(),
      firm: String(r.firm || r.company || "").trim(),
      role: String(r.role || r.title || "").trim(),
      city: String(r.city || "").trim(),
      state: String(r.state || "").trim(),
      notes: String(r.notes || "").trim(),
      createdAt: FieldValue.serverTimestamp(),
    });
    added++;
  }
  await logEvent("import", `+${added}, dupes ${duplicates}, suppressed ${suppressed}, bad ${invalid}`);
  return { added, duplicates, suppressed, invalid };
});

exports.enrollAll = onCall(async (request) => {
  const cfg = await requireOwner(request);
  const sequence = request.data.sequence || "ceu_intro";
  const seqSnap = await db.doc(`outreach_sequences/${sequence}`).get();
  if (!seqSnap.exists) throw new HttpsError("not-found", `No sequence '${sequence}'.`);
  const variants = seqSnap.data().variants || ["A"];

  const existing = await db.collection("outreach_enrollments")
    .where("sequence", "==", sequence).get();
  const enrolledIds = new Set(existing.docs.map((d) => d.data().contactId));
  let n = existing.size, enrolled = 0, skippedSupp = 0;

  const contacts = await db.collection("outreach_contacts").get();
  for (const c of contacts.docs) {
    if (enrolledIds.has(c.id)) continue;
    const data = c.data();
    if ((await db.doc(`outreach_suppression/${data.email}`).get()).exists) {
      skippedSupp++; continue;
    }
    const first = nextWindowOpen(cfg,
      new Date(Date.now() + Math.abs(jitterMs(cfg))));
    await db.collection("outreach_enrollments").add({
      contactId: c.id, sequence, status: "active", currentTouch: 0,
      variant: variants[n % variants.length],
      nextSendAt: Timestamp.fromDate(first),
      contactName: `${data.firstName} ${data.lastName}`.trim(),
      firm: data.firm || "",
      startedAt: FieldValue.serverTimestamp(),
    });
    n++; enrolled++;
  }
  await logEvent("enroll_all", `${sequence}: +${enrolled}, suppressed ${skippedSupp}`);
  return { enrolled, alreadyEnrolled: existing.size, suppressed: skippedSupp };
});

exports.enrollOne = onCall(async (request) => {
  const cfg = await requireOwner(request);
  const contactId = request.data.contactId;
  const sequence = request.data.sequence || "ceu_intro";
  const contactSnap = await db.doc(`outreach_contacts/${contactId}`).get();
  if (!contactSnap.exists) throw new HttpsError("not-found", "No such contact.");
  const c = contactSnap.data();
  if ((await db.doc(`outreach_suppression/${c.email}`).get()).exists) {
    throw new HttpsError("failed-precondition", "Contact is on the suppression list.");
  }
  const existing = await db.collection("outreach_enrollments")
    .where("contactId", "==", contactId).where("sequence", "==", sequence)
    .limit(1).get();
  if (!existing.empty) return { status: "already_enrolled" };
  const seqSnap = await db.doc(`outreach_sequences/${sequence}`).get();
  if (!seqSnap.exists) {
    throw new HttpsError("not-found", `No sequence '${sequence}' — run Seed defaults first.`);
  }
  const variants = seqSnap.data().variants || ["A"];
  const n = (await db.collection("outreach_enrollments")
    .where("sequence", "==", sequence).count().get()).data().count;
  const first = nextWindowOpen(cfg, new Date(Date.now() + Math.abs(jitterMs(cfg))));
  await db.collection("outreach_enrollments").add({
    contactId, sequence, status: "active", currentTouch: 0,
    variant: variants[n % variants.length],
    nextSendAt: Timestamp.fromDate(first),
    contactName: `${c.firstName} ${c.lastName}`.trim(), firm: c.firm || "",
    startedAt: FieldValue.serverTimestamp(),
  });
  await logEvent("enroll", `${c.email} \u2192 ${sequence}`);
  return { status: "enrolled", firstSendAt: first.toISOString() };
});

/* --------------------- Microsoft device-code connect --------------------- */

exports.msAuthStart = onCall(async (request) => {
  const cfg = await requireOwner(request);
  if (!cfg.tenantId || !cfg.clientId) {
    throw new HttpsError("failed-precondition",
      "Enter Tenant ID and Client ID in Settings first.");
  }
  const body = new URLSearchParams({
    client_id: cfg.clientId,
    scope: MS_SCOPES + " https://graph.microsoft.com/User.Read",
  });
  const r = await fetch(
    `https://login.microsoftonline.com/${cfg.tenantId}/oauth2/v2.0/devicecode`,
    { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body },
  );
  const j = await r.json();
  if (!j.device_code) {
    throw new HttpsError("internal", "Device flow failed: " + JSON.stringify(j).slice(0, 300));
  }
  await db.doc("outreach_private/authflow").set({
    deviceCode: j.device_code, startedAt: FieldValue.serverTimestamp(),
  });
  return {
    userCode: j.user_code,
    verificationUri: j.verification_uri || "https://microsoft.com/devicelogin",
    message: j.message || "",
  };
});

exports.msAuthPoll = onCall(async (request) => {
  const cfg = await requireOwner(request);
  const flow = await db.doc("outreach_private/authflow").get();
  if (!flow.exists) return { status: "error", message: "No sign-in in progress." };
  const body = new URLSearchParams({
    client_id: cfg.clientId,
    grant_type: "urn:ietf:params:oauth:grant-type:device_code",
    device_code: flow.data().deviceCode,
  });
  const r = await fetch(
    `https://login.microsoftonline.com/${cfg.tenantId}/oauth2/v2.0/token`,
    { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body },
  );
  const j = await r.json();
  if (j.error === "authorization_pending" || j.error === "slow_down") {
    return { status: "pending" };
  }
  if (j.refresh_token) {
    await db.doc("outreach_private/ms_token").set({
      refreshToken: j.refresh_token, connectedAt: FieldValue.serverTimestamp(),
    });
    await db.doc("outreach_private/authflow").delete();
    await logEvent("mailbox", "connected");
    return { status: "connected" };
  }
  return { status: "error", message: j.error_description || j.error || "Unknown error" };
});

/* ------------------------- exported for testing -------------------------- */
exports._test = {
  tzParts, localToUtc, inSendWindow, nextWindowOpen,
  renderTemplate, classify, localDateKey,
};
