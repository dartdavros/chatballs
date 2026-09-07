import { api, apiUpload } from "../../api/client";
import type { AuditPayload, AuditQuery, OrganizationSettings } from "./model";

const BASE = "/api/v1/company/administration/";

export async function loadOrganizationSettings(): Promise<{
  organization: OrganizationSettings;
  timezones: string[];
}> {
  return api<{ organization: OrganizationSettings; timezones: string[] }>(BASE);
}

export async function saveOrganizationSettings(
  settings: OrganizationSettings,
): Promise<OrganizationSettings> {
  const payload = await api<{ organization: OrganizationSettings }>(BASE, {
    method: "PATCH",
    body: JSON.stringify({
      name: settings.name,
      timezone: settings.timezone,
      currency: settings.currency,
    }),
  });
  return payload.organization;
}

export async function uploadOrganizationLogo(file: File): Promise<OrganizationSettings> {
  const form = new FormData();
  form.append("file", file);
  const payload = await apiUpload<{ organization: OrganizationSettings }>(
    `${BASE}logo/`,
    form,
  );
  return payload.organization;
}

export async function removeOrganizationLogo(): Promise<OrganizationSettings> {
  const payload = await api<{ organization: OrganizationSettings }>(
    `${BASE}logo/`,
    { method: "DELETE" },
  );
  return payload.organization;
}

export async function loadAudit(query: AuditQuery): Promise<AuditPayload> {
  const params = new URLSearchParams();
  if (query.q.trim()) params.set("q", query.q.trim());
  // «Всё время» — это отсутствие периода, а не отдельный период на сервере.
  if (query.period !== "all") params.set("period", query.period);
  if (query.category) params.set("category", query.category);
  if (query.actor) params.set("actor", query.actor);
  if (query.result) params.set("result", query.result);
  if (query.page > 1) params.set("page", String(query.page));
  const suffix = params.toString();
  return api<AuditPayload>(`${BASE}audit/${suffix ? `?${suffix}` : ""}`);
}
