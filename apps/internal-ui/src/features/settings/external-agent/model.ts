import { api } from "../../../api/client";

export type FieldRef = { sourceConnectionId: number; fieldId: string };
export type ExternalBinding = {
  agentId: number; channelId: number; agentName: string; externalAgentId: string;
  enabled: boolean; revision: number; policyVersion: number; policyAccepted: boolean;
  standardFields: string[]; customFields: FieldRef[]; templateIds: string[];
  staleGrants?: { customFields: FieldRef[]; templateIds: string[] };
  previousFields?: (FieldRef & { sourceName: string; label: string; type: string })[];
  proactiveEnabled: boolean; processingMode: "ordinary" | "long";
  ordinaryTimeout: number; longTimeout: number; maximumTimeout: number;
};
export type ExternalConnection = {
  id: number; name: string; baseUrl: string; enabled: boolean; revision: number;
  keyConfigured: boolean; compatible: boolean; checkedAt: string | null;
  contentTypes: string[]; bindings: ExternalBinding[];
  checkFailure?: "access" | "unavailable" | "incompatible" | null;
};
export type SettingsCatalog = {
  agents: { id: number; channelId: number; name: string }[];
  sources: { id: number; name: string }[];
  customFields: (FieldRef & { sourceName: string; label: string; type: string; options?: { value: string; label: string }[] })[];
  templates: { id: string; name: string; skillId: string; revision: number; purpose: string }[];
};
export type ExternalSettings = { enabled: boolean; version: number; connections: ExternalConnection[]; catalog: SettingsCatalog };
export type AccessDraft = { name: string; baseUrl: string; outboundKey: string };
export type ConnectionDraft = ExternalConnection & { outboundKey?: string };
export const pathFor = (organization: string) => `/api/v1/organizations/${organization}/settings/external-execution/`;
export const fetchSettings = (organization: string, signal?: AbortSignal) => api<ExternalSettings>(pathFor(organization), { signal });
export const changeFeature = (organization: string, enabled: boolean) => api<ExternalSettings>(pathFor(organization), {
  method: "PATCH", body: JSON.stringify({ enabled }),
});
export const createConnection = (organization: string, draft: AccessDraft) => api<{ connection: ExternalConnection }>(
  `${pathFor(organization)}connections/`, { method: "POST", body: JSON.stringify(draft) },
);
export const connectionAction = (organization: string, id: number, action: "check" | "key", method = "POST") =>
  api<{ connection: ExternalConnection; incomingKey?: string } | undefined>(`${pathFor(organization)}connections/${id}/${action}/`, {
    method, ...(method === "POST" ? { body: "{}" } : {}),
  });
