import type { siteEventsRu } from "./site-events.ru";
export const siteEventsEn: Record<keyof typeof siteEventsRu, string> = {
  "site_events.invitation": "Invitation",
  "site_events.accept": "Start chat",
  "site_events.dismiss": "Dismiss invitation",
  "site_events.failed": "Could not start the reply. Send a message and we will help.",
  "site_events.unavailable": "The assistant is unavailable right now. You can send a message.",
  "site_events.expired": "This invitation has expired. You can start a chat.",
};
