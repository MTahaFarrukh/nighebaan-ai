import { createServer } from "node:http";
import { createHmac, timingSafeEqual } from "node:crypto";
import { fileURLToPath } from "node:url";
import QRCode from "qrcode";
import qrTerminal from "qrcode-terminal";
import makeWASocket, {
  Browsers,
  DisconnectReason,
  downloadContentFromMessage,
  getContentType,
  fetchLatestBaileysVersion,
  useMultiFileAuthState,
} from "@whiskeysockets/baileys";

const env = process.env;
const key = env.WHATSAPP_API_KEY;
const account = normalizeJid(env.WHATSAPP_DEMO_JID);
const guardian = normalizeJid(env.WHATSAPP_GUARDIAN_JID);
const valid = value => /^[1-9][0-9]{6,14}@s\.whatsapp\.net$/.test(value ?? "");
const validIncoming = value => valid(value) || /^[0-9]{6,20}@lid$/.test(value ?? "");

if (!key || key.length < 32 || !valid(account) || !valid(guardian) || account === guardian || env.WHATSAPP_OWNER_OPT_IN !== "true") {
  console.error("Set a strong bridge key, distinct dedicated demo and guardian JIDs, and owner opt-in.");
  process.exit(1);
}

const hash = value => createHmac("sha256", key).update(value).digest("hex");
const guardianHash = hash(guardian);
const maxBytes = 25 * 1024 * 1024;
const allowedOrigin = "http://localhost:5173";
const authPath = fileURLToPath(new URL("./auth_baileys", import.meta.url));

let active = false;
let socket = null;
let reconnectTimer = null;
let pairing = { status: "connecting", qr: null, expires: 0 };
let eventQueue = Promise.resolve();
let pending = 0;

function normalizeJid(value) {
  if (typeof value !== "string") return "";
  const normalized = value.replace(/@c\.us$/, "@s.whatsapp.net");
  return normalized.replace(/:\d+(?=@s\.whatsapp\.net$)/, "");
}

const backendBase = (env.BACKEND_API_URL || "http://127.0.0.1:8000/api").replace(/\/$/, "");

async function api(path, body) {
  const json = body !== undefined && !(body instanceof FormData);
  const response = await fetch(backendBase + path, {
    method: body === undefined ? "GET" : "POST",
    headers: { "X-API-Key": key, ...(json ? { "Content-Type": "application/json" } : {}) },
    body: json ? JSON.stringify(body) : body,
    signal: AbortSignal.timeout(300000),
  });
  if (!response.ok) throw new Error("Bridge request failed");
  return response.json();
}

async function enableConfiguredGuardian() {
  const state = await api("/consent", { guardian: guardianHash, enabled: true });
  if (state.enabled) console.log("Configured guardian enabled from environment.");
  return state.enabled;
}

function unwrapMessage(message) {
  let current = message;
  while (current?.ephemeralMessage || current?.viewOnceMessage || current?.documentWithCaptionMessage) {
    current = current.ephemeralMessage?.message ?? current.viewOnceMessage?.message ?? current.documentWithCaptionMessage?.message;
  }
  return current ?? {};
}

function textFromMessage(message) {
  const content = unwrapMessage(message);
  if (content.conversation) return content.conversation;
  return content.extendedTextMessage?.text;
}

function mediaFromMessage(message) {
  const content = unwrapMessage(message);
  const type = getContentType(content);
  const supported = { imageMessage: "image", videoMessage: "video", audioMessage: "audio", documentMessage: "document" };
  return supported[type]
    ? { content: content[type], type: supported[type], caption: String(content[type].caption || "").trim() }
    : null;
}

async function mediaForm(message, sender) {
  const media = mediaFromMessage(message.message);
  if (!media) return null;
  const stream = await downloadContentFromMessage(media.content, media.type);
  const chunks = [];
  let size = 0;
  for await (const chunk of stream) {
    size += chunk.length;
    if (size > maxBytes || !active) return null;
    chunks.push(chunk);
  }
  const form = new FormData();
  form.set("guardian", guardianHash);
  form.set("sender", hash(sender));
  if (media.caption) form.set("caption", media.caption);
  form.set("file", new Blob(chunks, { type: media.content?.mimetype ?? "application/octet-stream" }), "media");
  return form;
}

async function handleMessage(message) {
  if (!active || !socket || message.key?.fromMe) return;
  const remoteJid = normalizeJid(message.key?.remoteJid);
  if (!remoteJid || remoteJid === "status@broadcast" || remoteJid.endsWith("@g.us") || remoteJid.endsWith("@broadcast")) return;
  const timestamp = Number(message.messageTimestamp);
  if (!Number.isFinite(timestamp) || Math.abs(Date.now() / 1000 - timestamp) > 300) return;

  const sender = normalizeJid(message.key?.participant || remoteJid);
  if (!validIncoming(sender)) return;
  if (sender === guardian) return;
  console.log(JSON.stringify({ event: "incoming_message_received", sender_type: sender.endsWith("@lid") ? "lid" : "phone_jid" }));

  const text = textFromMessage(message.message);
  if (!(await api("/consent?guardian=" + guardianHash)).enabled) return;
  let decision;
  if (typeof text === "string" && text.trim() && text.length <= 12000) {
    decision = await api("/whatsapp/event", { guardian: guardianHash, sender: hash(sender), text });
  } else {
    const form = await mediaForm(message, sender);
    if (!form) return;
    decision = await api("/whatsapp/media", form);
  }
  console.log(JSON.stringify({
    event: "message_analyzed",
    risk_level: decision.risk_level,
    rule_ids: decision.rule_ids,
    should_alert: decision.should_alert,
    dry_run: decision.dry_run,
    history_recorded: decision.history_recorded,
  }));
  if (!decision.should_alert || !["medium", "high"].includes(decision.risk_level)) return;
  if (decision.dry_run || env.DRY_RUN !== "false") {
    console.log("Dry-run: high-risk alert reserved; no delivery.");
    return;
  }
  if (!active || !(await api("/consent?guardian=" + guardianHash)).enabled) return;
  try {
    const selfJid = normalizeJid(socket.user?.id) || account;
    await socket.sendMessage(selfJid, { text: decision.alert_user_text });
    await socket.sendMessage(guardian, { text: decision.alert_guardian_text });
  } catch {
    console.error("Could not deliver the high-risk alert.");
  }
}

const pairingServer = createServer(async (req, res) => {
  res.setHeader("Cache-Control", "no-store");
  if (req.url !== "/pairing" || req.headers.origin !== allowedOrigin) {
    res.writeHead(404).end();
    return;
  }
  res.setHeader("Access-Control-Allow-Origin", allowedOrigin);
  res.setHeader("Vary", "Origin");
  if (req.method === "OPTIONS") {
    res.setHeader("Access-Control-Allow-Headers", "X-API-Key");
    res.setHeader("Access-Control-Allow-Methods", "GET");
    res.writeHead(204).end();
    return;
  }
  const provided = Buffer.from(req.headers["x-api-key"] ?? "");
  const expected = Buffer.from(key);
  if (req.method !== "GET" || provided.length !== expected.length || !timingSafeEqual(provided, expected)) {
    res.writeHead(401).end();
    return;
  }
  try {
    const current = pairing;
    const image = current.qr && Date.now() < current.expires ? await QRCode.toDataURL(current.qr, { width: 320, margin: 4 }) : null;
    let guardianEnabled = null;
    if (active) {
      guardianEnabled = await api("/consent?guardian=" + guardianHash)
        .then(state => state.enabled ? true : enableConfiguredGuardian())
        .catch(() => null);
    }
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({
      status: pairing.status,
      qr: current === pairing && Date.now() < current.expires ? image : null,
      guardian_enabled: active ? guardianEnabled : null,
      guardian_command: null,
      dry_run: env.DRY_RUN !== "false",
    }));
  } catch {
    res.writeHead(500).end();
  }
});

function scheduleReconnect() {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    void connect();
  }, 5000);
}

async function connect() {
  const { state, saveCreds } = await useMultiFileAuthState(authPath);
  const { version } = await fetchLatestBaileysVersion().catch(() => ({ version: undefined }));
  socket = makeWASocket({
    auth: state,
    ...(version ? { version } : {}),
    browser: Browsers.ubuntu("Nigehbaan AI"),
    connectTimeoutMs: 60000,
    defaultQueryTimeoutMs: 120000,
    retryRequestDelayMs: 1000,
    fireInitQueries: false,
    printQRInTerminal: false,
    syncFullHistory: false,
    markOnlineOnConnect: false,
  });
  socket.ev.on("creds.update", saveCreds);
  socket.ev.on("connection.update", ({ connection, lastDisconnect, qr }) => {
    if (qr) {
      active = false;
      pairing = { status: "waiting for scan", qr, expires: Date.now() + 20000 };
      qrTerminal.generate(qr, { small: true });
    }
    if (connection === "connecting") pairing = { status: "connecting", qr: null, expires: 0 };
    if (connection === "open") {
      const linked = normalizeJid(socket.user?.id);
      if (linked !== account) {
        active = false;
        pairing = { status: "wrong account", qr: null, expires: 0 };
        void socket.logout().catch(() => {});
        return;
      }
      active = true;
      pairing = { status: "connected", qr: null, expires: 0 };
      console.log("Dedicated WhatsApp account connected through Baileys.");
      void enableConfiguredGuardian().catch(() => console.error("Could not enable configured guardian."));
    }
    if (connection === "close") {
      active = false;
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const loggedOut = statusCode === DisconnectReason.loggedOut;
      pairing = { status: loggedOut ? "logged out" : "disconnected", qr: null, expires: 0 };
      if (!loggedOut) scheduleReconnect();
    }
  });
  socket.ev.on("messages.upsert", ({ messages, type }) => {
    if (!active || type !== "notify" || pending >= 20) return;
    for (const message of messages) {
      pending++;
      eventQueue = eventQueue.then(() => handleMessage(message))
        .catch(() => console.error("A WhatsApp event could not be processed safely."))
        .finally(() => pending--);
    }
  });
}

pairingServer.on("error", () => { console.error("Cannot start the local pairing endpoint."); process.exit(1); });
pairingServer.listen(8011, "127.0.0.1", () => { void connect(); });

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.once(signal, () => {
    active = false;
    pairingServer.close();
    if (reconnectTimer) clearTimeout(reconnectTimer);
    socket?.ws?.close();
    process.exit(0);
  });
}
