import type { SiteEvent } from "@chatballs/contracts";

export async function sendEvent(token: string, event: SiteEvent, hostOrigin: string) {
  const response = await fetch("/api/v1/webchat/site-events/", { method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ name: event.name, eventId: event.eventId, data: event.data, hostOrigin }) });
  if (!response.ok) throw new Error("site_event_rejected");
  return (await response.json()).state as "accepted" | "duplicate" | "suppressed";
}

export async function cancelEvent(token: string, hostOrigin: string) {
  await fetch("/api/v1/webchat/site-events/cancel/", { method: "POST", keepalive: true,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ hostOrigin }) });
}
