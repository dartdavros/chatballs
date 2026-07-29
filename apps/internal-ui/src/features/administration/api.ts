import { api, apiUpload } from "../../api/client";
import type {
  AuditEvent,
  OrganizationSettings,
  SubscriptionSummary,
} from "./model";

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

export async function loadSubscription(): Promise<SubscriptionSummary> {
  const payload = await api<{ subscription: SubscriptionSummary }>(
    `${BASE}subscription/`,
  );
  return payload.subscription;
}

export async function loadAudit(): Promise<AuditEvent[]> {
  const payload = await api<{ items: AuditEvent[] }>(`${BASE}audit/`);
  return payload.items;
}
