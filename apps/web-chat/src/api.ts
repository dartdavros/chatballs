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

export type WebMessage = { id: number; author: "client" | "ai" | "operator" | "system"; text: string; createdAt: string };
export type Poll = { state: "ai" | "operator" | "waiting"; lifecycle: string; messages: WebMessage[] };

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

export async function poll(token: string, since: number): Promise<Poll> {
  const r = await fetch(`${API}/messages/?since=${since}`, { headers: { Authorization: `Bearer ${token}` } });
  return r.json();
}
