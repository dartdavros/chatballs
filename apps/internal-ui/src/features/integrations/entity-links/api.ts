import { api } from "../../../api/client";

export type EntityLink = { id: number; name: string; service: string; revision: number; searchable: boolean; url: string };
export type Candidate = { id: string; label: string };
const base = "/api/v1/integrations/entity-links/";
export const listLinks = (conversation: number) => api<{ items: EntityLink[] }>(`${base}?conversation=${conversation}`);
export const searchLinks = (link: number, conversation: number, query: string, triggerKey: string) => api<{ runId: string }>(`${base}${link}/search/?conversation=${conversation}`,
  { method: "POST", body: JSON.stringify({ query, triggerKey }) });
export const candidates = (link: number, conversation: number, run: string) => api<{ state: string; items: Candidate[] }>(`${base}${link}/search/?${new URLSearchParams({ conversation: String(conversation), run })}`);
export const updateLink = (link: EntityLink, conversation: number, body: object) => api(`${base}${link.id}/?conversation=${conversation}`,
  { method: "POST", body: JSON.stringify({ ...body, revision: link.revision }) });
