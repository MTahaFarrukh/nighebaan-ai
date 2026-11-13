import makeWASocket, { DisconnectReason, downloadMediaMessage, jidNormalizedUser, useMultiFileAuthState } from "@whiskeysockets/baileys";
import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { fileURLToPath } from "node:url";
import pino from "pino";
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
const logger = pino({level:"silent"});
const hash = value => createHmac("sha256", key).update(value).digest("hex");
const guardianHash = hash(guardian);
const code = randomBytes(12).toString("hex");
const codeExpiry = Date.now() + 15 * 60 * 1000;
let codeUsed = false;
console.log("Guardian opt-in command, expires in 15 minutes: NIGEHBAAN %s",code);
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
const {state,saveCreds} = await useMultiFileAuthState(fileURLToPath(new URL("./auth_demo",import.meta.url)));
let retries = 0;
let active = false;
let generation = 0;
const maxBytes = 25 * 1024 * 1024;

async function handle(socket, message, current) {
  if (current !== generation || !active || message.key.fromMe || !message.message) return;
  const timestamp = Number(message.messageTimestamp);
  if (!Number.isFinite(timestamp) || Math.abs(Date.now() / 1000 - timestamp) > 300) return;
  const jid = jidNormalizedUser(message.key.remoteJid ?? "");
  const alternate = jidNormalizedUser(message.key.remoteJidAlt ?? "");
  const sender = valid(alternate) ? alternate : jid;
  if (!valid(sender) || !(valid(jid) || jid.endsWith("@lid"))) return;
  const payload = message.message;
  const text = payload.conversation ?? payload.extendedTextMessage?.text;
  if (sender === guardian) {
    if (text?.trim().toUpperCase() === "STOP") {
      await api("/consent",{guardian:guardianHash,enabled:false});
    } else if (!codeUsed && Date.now()<codeExpiry && typeof text==="string") {
      const candidate = Buffer.from(text.trim());
      const expected = Buffer.from("NIGEHBAAN "+code);
      if (candidate.length===expected.length && timingSafeEqual(candidate,expected)) {
        const status=await api("/consent",{guardian:guardianHash,enabled:true});
        codeUsed=status.enabled;
      }
    }
    return;
  }
  const path="/consent?guardian="+guardianHash;
  if (!(await api(path)).enabled) return;
  let decision;
  if (typeof text==="string" && text.trim() && text.length<=12000) {
    decision=await api("/whatsapp/event",{guardian:guardianHash,sender:hash(sender),text});
  } else {
    const item=payload.imageMessage ?? payload.audioMessage ?? payload.videoMessage ?? payload.documentMessage;
    if (!item || Number(item.fileLength ?? 0)>maxBytes) return;
    const stream=await downloadMediaMessage(message,"stream",{}, {logger});
    const chunks=[];
    let size=0;
    for await (const chunk of stream) {
      size+=chunk.length;
      if (size>maxBytes) {stream.destroy(); return;}
      chunks.push(chunk);
    }
    const form=new FormData();
    form.set("guardian",guardianHash);
    form.set("sender",hash(sender));
    form.set("file",new Blob(chunks,{type:item.mimetype?.split(";")[0] ?? "application/octet-stream"}),"media");
    decision=await api("/whatsapp/media",form);
  }
  if (!decision.should_alert) return;
  if (decision.dry_run || env.DRY_RUN !== "false") {
    console.log("Dry-run: high-risk alert reserved; no delivery.");
    return;
  }
  if (current !== generation || !active || !(await api(path)).enabled) return;
  await socket.sendMessage(account,{text:decision.alert_user_text});
  if (current === generation && active && (await api(path)).enabled) {
    await socket.sendMessage(guardian,{text:decision.alert_guardian_text});
  }
}

function connect() {
  const current=++generation;
  const socket=makeWASocket({auth:state,logger,markOnlineOnConnect:false,syncFullHistory:false,shouldSyncHistoryMessage:()=>false});
  socket.ev.on("creds.update",()=>void saveCreds().catch(()=>console.error("Could not save local pairing state.")));
  socket.ev.on("connection.update",({connection,qr,lastDisconnect})=>{
    if (current !== generation) return;
    if (qr) qrTerminal.generate(qr,{small:true});
    if (connection==="open") {
      active=jidNormalizedUser(socket.user?.id ?? "")===account;
      if (!active) {console.error("Paired account differs from the configured demo account."); generation++; socket.end(undefined); return;}
      retries=0;
      console.log("Dedicated WhatsApp account connected.");
    }
    if (connection==="close") {
      active=false;
      if (lastDisconnect?.error?.output?.statusCode===DisconnectReason.loggedOut || retries>=8) {
        console.log("WhatsApp disconnected. Review the local setup before restarting."); return;
      }
      setTimeout(connect,Math.min(30000,1000*2**retries++));
    }
  });
  let queue=Promise.resolve();
  let pending=0;
  socket.ev.on("messages.upsert",({type,messages,requestId})=>{
    if (type!=="notify" || requestId || !active) return;
    for (const message of messages) {
      if (pending>=20) break;
      pending++;
      queue=queue.then(()=>handle(socket,message,current))
        .catch(()=>console.error("A WhatsApp event could not be processed."))
        .finally(()=>pending--);
    }
  });
}

connect();
