const API = "/api/v1/webchat";

export type WebConfig = {
  available: boolean;
  reason?: string;
  channel?: string;
  title?: string;
  accent?: string;
  greeting?: string;
  consent?: { text: string; version: string };
  quickReplies?: string[];
  fallback?: { label: string; url: string }[];
};

// kind: "" — текст, "contact_request" — виджет рисует форму телефона, "contact" — клиент поделился номером.
export type WebMessage = { id: number; author: "client" | "ai" | "operator" | "system"; kind?: string; text: string; createdAt: string };

// Приглашение/состояние онлайн-звонка (SPEC-HUB-0013).
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

export async function getConfig(channel: string): Promise<WebConfig> {
  const r = await fetch(`${API}/config/?channel=${encodeURIComponent(channel)}`);
  return r.json();
}

export async function startSession(channel: string): Promise<string | null> {
  const r = await fetch(`${API}/session/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ channel }),
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

export async function sendContact(token: string, phone: string): Promise<boolean> {
  const r = await fetch(`${API}/contact/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ phone }),
  });
  return r.ok;
}

export async function poll(token: string, since: number): Promise<Poll> {
  const r = await fetch(`${API}/messages/?since=${since}`, { headers: { Authorization: `Bearer ${token}` } });
  return r.json();
}

// --- Онлайн-звонки (SPEC-HUB-0013): доставка приглашения и клиентские действия ---

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

// --- Support mode (SPEC-HUB-0010 §7): authenticated in-product chat ---

const SUPPORT_API = "/api/v1/support";

export type SupportSession = {
  conversation: { id: number; controlMode: string; messages: WebMessage[] };
  snapshot: { displayName: string; displayEmail: string; subjectKey: string };
  widgetCredential: string;
};

// Старт сессии: verify Product Support Token → conversation + widget-credential.
// При ошибке (invalid/expired token) → null (виджет покажет unavailable).
export async function startSupportSession(channel: string, token: string): Promise<SupportSession | null> {
  const r = await fetch(`${SUPPORT_API}/sessions/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ channel, token }),
  });
  if (!r.ok) return null;
  const data = await r.json();
  // controlMode → виджет-стейт (AI→ai, HUMAN→operator, PAUSED→waiting).
  const conv = data.conversation;
  const stateMap: Record<string, "ai" | "operator" | "waiting"> = { AI: "ai", HUMAN: "operator", PAUSED: "waiting" };
  return {
    conversation: {
      id: conv.id,
      controlMode: conv.controlMode,
      messages: (conv.messages ?? []).map((m: { id: number; author: string; text: string; createdAt: string }) => ({
        id: m.id,
        author: (m.author === "CONTACT" ? "client" : m.author === "OPERATOR" ? "operator" : m.author === "SYSTEM" ? "system" : "ai") as WebMessage["author"],
        text: m.text,
        createdAt: m.createdAt,
      })),
    },
    snapshot: { displayName: data.snapshot?.displayName ?? "", displayEmail: data.snapshot?.displayEmail ?? "", subjectKey: data.snapshot?.subjectKey ?? "" },
    widgetCredential: data.widgetCredential,
  };
}

export async function pollSupport(credential: string, since: number): Promise<Poll> {
  const r = await fetch(`${SUPPORT_API}/sessions/messages/?since=${since}`, { headers: { Authorization: `Bearer ${credential}` } });
  return r.json();
}

export async function sendSupport(credential: string, text: string): Promise<boolean> {
  const r = await fetch(`${SUPPORT_API}/sessions/messages/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${credential}` },
    body: JSON.stringify({ text }),
  });
  return r.ok;
}
