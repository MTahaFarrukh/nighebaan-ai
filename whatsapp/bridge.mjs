import { existsSync } from "node:fs";
import { createServer } from "node:http";
import QRCode from "qrcode";
import web from "whatsapp-web.js";
import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { fileURLToPath } from "node:url";
import qrTerminal from "qrcode-terminal";

const env = process.env;
const key = env.WHATSAPP_API_KEY;
const account = env.WHATSAPP_DEMO_JID;
const guardian = env.WHATSAPP_GUARDIAN_JID;
const valid = value => /^[1-9][0-9]{6,14}@s\.whatsapp\.net$/.test(value ?? "");
if (!key || key.length < 32 || !valid(account) || !valid(guardian) || account === guardian || env.WHATSAPP_OWNER_OPT_IN !== "true") {
  console.error("Set a strong bridge key, distinct dedicated demo and guardian JIDs, and owner opt-in.");
  process.exit(1);
}
const hash = value => createHmac("sha256", key).update(value).digest("hex");
const guardianHash = hash(guardian);
let code = "";
let codeExpiry = 0;
function renewConsentCode() {
  code = randomBytes(12).toString("hex");
  codeExpiry = Date.now() + 15 * 60 * 1000;
}
const consentPath = "/consent?guardian=" + guardianHash;
const api = async (path, body) => {
  const json = body !== undefined && !(body instanceof FormData);
  const response = await fetch("http://127.0.0.1:8000/api" + path, {
    method: body === undefined ? "GET" : "POST",
    headers: {"X-API-Key":key, ...(json ? {"Content-Type":"application/json"} : {})},
    body: json ? JSON.stringify(body) : body,
    signal: AbortSignal.timeout(300000),
  });
  if (!response.ok) throw new Error("Bridge request failed");
  return response.json();
};
const { Client, LocalAuth } = web;
let active = false;
const maxBytes = 25 * 1024 * 1024;

function configuredJid(id) {
  return typeof id === "string" ? id.replace(/@c\.us$/, "@s.whatsapp.net") : "";
}

async function handle(client, message) {
  if (!active || message.fromMe || message.isStatus || message.broadcast) return;
  const timestamp = Number(message.timestamp);
  if (!Number.isFinite(timestamp) || Math.abs(Date.now() / 1000 - timestamp) > 300) return;
  if (!/@(?:c\.us|lid)$/.test(message.from ?? "")) return;
  const sender = await resolveJid(client, message.from);
  if (!active || !valid(sender)) return;
  const text = message.type === "chat" ? message.body : undefined;
  if (sender === guardian) {
    if (text?.trim().toUpperCase() === "STOP") {
      await api("/consent",{guardian:guardianHash,enabled:false});
    } else if (code && Date.now()<codeExpiry && typeof text==="string") {
      const candidate = Buffer.from(text.trim());
      const expected = Buffer.from("NIGEHBAAN "+code);
      if (candidate.length===expected.length && timingSafeEqual(candidate,expected)) {
        const status=await api("/consent",{guardian:guardianHash,enabled:true});
        if (status.enabled) codeExpiry = 0;
      }
    }
    return;
  }
  const path = consentPath;
  if (!(await api(path)).enabled) return;
  let decision;
  if (typeof text==="string" && text.trim() && text.length<=12000) {
    decision=await api("/whatsapp/event",{guardian:guardianHash,sender:hash(sender),text});
  } else {
    if (!message.hasMedia || !["image", "video", "audio", "ptt", "document"].includes(message.type)) return;
    const media = await message.downloadMediaStream();
    if (!media) return;
    const chunks = [];
    let size = 0;
    for await (const chunk of media.stream) {
      size += chunk.length;
      if (size > maxBytes || !active) { media.stream.destroy(); return; }
      chunks.push(chunk);
    }
    const form=new FormData();
    form.set("guardian",guardianHash);
    form.set("sender",hash(sender));
    form.set("file",new Blob(chunks,{type:media.mimetype?.split(";")[0] ?? "application/octet-stream"}),"media");
    decision=await api("/whatsapp/media",form);
  }
  if (decision.risk_level !== "high" || !decision.should_alert) return;
  if (decision.dry_run || env.DRY_RUN !== "false") {
    console.log("Dry-run: high-risk alert reserved; no delivery.");
    return;
  }
  if (!active || !(await api(path)).enabled) return;
  try {
    await client.sendMessage(client.info.wid._serialized, decision.alert_user_text, { sendSeen: false });
  } catch {
    console.error("Could not deliver the self-chat alert.");
  }
  if (active && (await api(path)).enabled) {
    await client.sendMessage(guardian.replace("@s.whatsapp.net", "@c.us"), decision.alert_guardian_text, { sendSeen: false });
  }
}

let pairing = { status: "connecting", qr: null, expires: 0 };
const allowedOrigin = "http://localhost:5173";
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
    const image = current.qr && Date.now() < current.expires
      ? await QRCode.toDataURL(current.qr, { width: 320, margin: 4 })
      : null;
    let guardianEnabled = null;
    let guardianCommand = null;
    if (active) {
      guardianEnabled = await api(consentPath).then((state) => state.enabled).catch(() => null);
      if (active && guardianEnabled === false) {
        if (Date.now() >= codeExpiry) renewConsentCode();
        guardianCommand = "NIGEHBAAN " + code;
      }
    }
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({
      status: pairing.status,
      qr: current === pairing && Date.now() < current.expires ? image : null,
      guardian_enabled: active ? guardianEnabled : null,
      guardian_command: active ? guardianCommand : null,
      dry_run: env.DRY_RUN !== "false",
    }));
  } catch {
    res.writeHead(500).end();
  }
});

async function resolveJid(client, id) {
  if (!id?.endsWith("@lid")) return configuredJid(id);
  const [mapping] = await client.getContactLidAndPhone([id]);
  return configuredJid(mapping?.pn);
}

function connect() {
  const chromePath = env.WHATSAPP_CHROME_PATH ?? [
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  ].find((path) => process.platform === "win32" && existsSync(path));
  const client = new Client({
    authTimeoutMs: 120000,
    authStrategy: new LocalAuth({ dataPath: fileURLToPath(new URL(env.WHATSAPP_REPAIR_SESSION === "true" ? "./auth_browser_repair" : "./auth_browser", import.meta.url)) }),
    puppeteer: {
      headless: env.WHATSAPP_HEADLESS !== "false",
      ...(chromePath ? { executablePath: chromePath } : {}),
    },
    webVersionCache: { type: "none" },
  });
  client.on("qr", (qr) => {
    active = false;
    pairing = { status: "waiting for scan", qr, expires: Date.now() + 20000 };
    qrTerminal.generate(qr, { small: true });
  });
  client.on("authenticated", () => {
    pairing = { status: "verifying account", qr: null, expires: 0 };
  });
  const finish = (status) => {
    active = false;
    pairing = { status, qr: null, expires: 0 };
    void client.destroy().catch(() => {});
  };
  client.on("ready", () => {
    void resolveJid(client, client.info.wid._serialized).then((linked) => {
      if (pairing.status !== "verifying account" && pairing.status !== "connecting") return;
      if (linked !== account) { finish("wrong account"); return; }
      active = true;
      pairing = { status: "connected", qr: null, expires: 0 };
      console.log("Dedicated WhatsApp Web account connected.");
    }).catch(() => finish("could not verify account"));
  });
  client.on("auth_failure", () => finish("authentication failed"));
  client.on("disconnected", () => finish("disconnected"));
  let queue = Promise.resolve();
  let pending = 0;
  client.on("message", (message) => {
    if (!active || pending >= 20) return;
    pending++;
    queue = queue.then(() => handle(client, message))
      .catch(() => console.error("A WhatsApp event could not be processed."))
      .finally(() => pending--);
  });
  void client.initialize().catch((error) => {
    console.error(error?.name === "TimeoutError" ? "WhatsApp Web did not initialize before the timeout." : "WhatsApp Web initialization failed.");
    console.error("Could not start WhatsApp Web Chromium. Check the browser installation.");
    finish("browser startup failed");
  });
  for (const signal of ["SIGINT", "SIGTERM"]) {
    process.once(signal, () => {
      active = false;
      pairingServer.close();
      void client.destroy().catch(() => {}).finally(() => process.exit(0));
    });
  }
}

pairingServer.on("error", () => { console.error("Cannot start the local pairing endpoint."); process.exit(1); });
pairingServer.listen(8011, "127.0.0.1", connect);
