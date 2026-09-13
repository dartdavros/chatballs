import { api, apiUpload } from "../../api/client";
import type { AuthenticatedUser } from "../../types";

// Создание организации идёт без организации в адресе: её ещё нет. Клиент
// такие пути не переписывает (namespace «organizations» не тенантный).
const BASE = "/api/v1/organizations/";

export type OrganizationCreateOptions = {
  timezones: string[];
  languages: Array<{ code: string; label: string }>;
  currencies: string[];
};

export type OrganizationDraft = {
  name: string;
  timezone: string;
  currency: string;
  // Пустая строка — «как в установке».
  language: string;
};

export type OrganizationCreated = {
  user: AuthenticatedUser;
  organizationPublicId: string;
};

export function loadOrganizationCreateOptions(): Promise<OrganizationCreateOptions> {
  return api<OrganizationCreateOptions>(`${BASE}options/`);
}

export function createOrganization(draft: OrganizationDraft): Promise<OrganizationCreated> {
  return api<OrganizationCreated>(BASE, {
    method: "POST",
    body: JSON.stringify(draft),
  });
}

/** Логотип загружается уже в созданную организацию — по её полному адресу,
 *  а не по активной: интерфейс ещё в прежней. */
export function uploadNewOrganizationLogo(organizationPublicId: string, file: File): Promise<unknown> {
  const form = new FormData();
  form.append("file", file);
  return apiUpload(`${BASE}${organizationPublicId}/company/administration/logo/`, form);
}
