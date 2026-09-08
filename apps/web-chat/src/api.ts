const API = "/api/v1/webchat";

export type WidgetFeatures = { voiceMessages: boolean; audioCalls: boolean; videoCalls: boolean };

export type WebConfig = {
  features?: WidgetFeatures;
  available: boolean;
  reason?: string;
  widgetKey?: string;
  title?: string;
  accent?: string;
  greeting?: string;
  consent?: { text: string; version: string };
  quickReplies?: string[];
  fallback?: { label: string; url: string }[];
};

// kind: "" — текст, "contact_request" — виджет рисует форму телефона,
// "contact" — клиент поделился номером, "VOICE" — голосовое (см. hasAudio).
export type WebAttachment = { name: string; contentType: string; size: number; available: boolean };
export type WebMessage = { id: number; author: "client" | "ai" | "operator" | "system"; kind?: string; text: string; createdAt: string; durationSeconds?: number; hasAudio?: boolean; attachment?: WebAttachment };

// Приглашение/состояние онлайн-звонка (SPEC-CHATBALLS-0013).
export type CallKind = "AUDIO" | "VIDEO";
export type CallInfo = {
  callId: string;
  status: string;
  kind: CallKind;
  expiresAt?: string;
  staffName?: string;
  endedBy?: string | null;
  durationSeconds?: number | null;
};

export function callKindOf(call: CallInfo | null | undefined): CallKind | null {
  return call?.kind === "AUDIO" || call?.kind === "VIDEO" ? call.kind : null;
}

export const isVideoCall = (call: CallInfo | null | undefined): boolean => callKindOf(call) === "VIDEO";

export type CallBootstrap = { call: CallInfo; accessToken: string; iceServers: RTCIceServer[] };
export type CallStateEnvelope = { call: CallInfo; iceServers: RTCIceServer[] };

export type Poll = { state: "ai" | "operator" | "waiting"; lifecycle: string; messages: WebMessage[]; call?: CallInfo | null };

export type WidgetEntry = { widgetKey?: string; channel?: string };

function entryQuery(entry: WidgetEntry): string {
  if (entry.widgetKey) return `widgetKey=${encodeURIComponent(entry.widgetKey)}`;
  return `channel=${encodeURIComponent(entry.channel ?? "")}`;
}

export async function getConfig(entry: WidgetEntry, hostOrigin: string): Promise<WebConfig> {
  const r = await fetch(`${API}/config/?${entryQuery(entry)}&hostOrigin=${encodeURIComponent(hostOrigin)}`);
  return r.json();
}

export async function startSession(entry: WidgetEntry, hostOrigin: string): Promise<string | null> {
  const r = await fetch(`${API}/session/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...entry, hostOrigin }),
  });
  if (!r.ok) return null;
  return (await r.json()).token as string;
}

export async function sendMessage(token: string, text: string): Promise<boolean> {
  const r = await fetch(`${API}/messages/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ text }),
  });
  return r.ok;
}

export async function sendVoice(token: string, audio: Blob, durationSeconds: number): Promise<boolean> {
  const body = new FormData();
  const type = (audio.type || "audio/webm").split(";")[0];
  body.append("audio", audio, `voice.${type.split("/")[1] || "webm"}`);
  body.append("duration", String(Math.round(durationSeconds)));
  const r = await fetch(`${API}/messages/`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body });
  return r.ok;
}

export const MAX_FILE_BYTES = 20 * 1024 * 1024;

// Файл или фото из виджета: multipart file + подпись text.
export async function sendFile(token: string, file: File, caption: string): Promise<boolean> {
  const body = new FormData();
  body.append("file", file, file.name);
  if (caption) body.append("text", caption);
  const r = await fetch(`${API}/messages/`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body });
  return r.ok;
}

// URL вложения: <img src>/<a href> не умеют заголовки — токен идёт параметром.
export function attachmentUrl(token: string, messageId: number, inline = false): string {
  return `${API}/messages/${messageId}/attachment/?token=${encodeURIComponent(token)}${inline ? "&inline" : ""}`;
}

// URL аудио голосового: <audio src> не умеет заголовки — токен идёт параметром.
export function voiceAudioUrl(token: string, messageId: number): string {
  return `${API}/messages/${messageId}/audio/?token=${encodeURIComponent(token)}`;
}

export async function sendContact(token: string, phone: string): Promise<boolean> {
  const r = await fetch(`${API}/contact/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ phone }),
  });
  return r.ok;
}

// Сессия виджета живёт, пока ей пользуются; после долгого простоя сервер её
// не признаёт, и виджету надо не «зависнуть», а предложить начать заново.
export class SessionExpired extends Error {}

export async function poll(token: string, since: number): Promise<Poll> {
  const r = await fetch(`${API}/messages/?since=${since}`, { headers: { Authorization: `Bearer ${token}` } });
  // 401 (сессии нет) и 429 (лимит) отвечают {"detail": ...}, а не лентой:
  // без этой проверки тело уходило бы в ingestPoll как пустой Poll.
  if (r.status === 401) throw new SessionExpired("webchat session is gone");
  if (!r.ok) throw new Error(`poll failed: ${r.status}`);
  return r.json();
}

// --- Онлайн-звонки (SPEC-CHATBALLS-0013): доставка приглашения и клиентские действия ---

const CALLS_API = "/api/v1/calls";

// Виджет: получить call access token по session token (переход на страницу звонка).
export async function openWebchatCall(sessionToken: string): Promise<CallBootstrap | null> {
  const r = await fetch(`${API}/call/open/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionToken}` },
  });
  if (!r.ok) return null;
  return r.json();
}

// Виджет: отклонить приглашение, не открывая страницу звонка.
export async function declineWebchatCall(sessionToken: string): Promise<boolean> {
  const r = await fetch(`${API}/call/decline/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionToken}` },
  });
  return r.ok;
}

// Страница звонка: обмен invite token из ссылки TG/MAX на access token.
export async function resolveCallInvite(inviteToken: string): Promise<CallBootstrap | null> {
  const r = await fetch(`${CALLS_API}/invites/resolve/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: inviteToken }),
  });
  if (!r.ok) return null;
  return r.json();
}

async function callAccessAction(action: "accept" | "decline" | "end", accessToken: string): Promise<CallInfo> {
  const r = await fetch(`${CALLS_API}/access/${action}/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
  });
  if (!r.ok) {
    const payload = await r.json().catch(() => ({ detail: "Не удалось выполнить действие со звонком" })) as { detail?: string };
    throw new Error(payload.detail || "Не удалось выполнить действие со звонком");
  }
  return (await r.json()).call as CallInfo;
}

export async function fetchCallState(accessToken: string): Promise<CallStateEnvelope | null> {
  const r = await fetch(`${CALLS_API}/access/state/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
  });
  if (!r.ok) return null;
  return r.json();
}
export const acceptCall = (accessToken: string) => callAccessAction("accept", accessToken);
export const declineCall = (accessToken: string) => callAccessAction("decline", accessToken);
export const endCall = (accessToken: string) => callAccessAction("end", accessToken);
