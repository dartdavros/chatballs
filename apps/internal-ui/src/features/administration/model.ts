import type { RouteKey, SessionUser } from "../../types";
import { hasCapability } from "../../auth/access";

export type AdministrationRoute = Extract<RouteKey, "administrationAudit">;

export type AdministrationSection = "organization" | "audit";

export type OrganizationSettings = {
  name: string;
  timezone: string;
  currency: string;
  logoUrl: string | null;
};

export type AuditEvent = {
  id: number;
  createdAt: string;
  actor: string;
  action: string;
  result: "SUCCESS" | "DENIED" | "FAILED";
  resultLabel: string;
};

export function administrationSection(route: AdministrationRoute): AdministrationSection {
  if (route === "administrationAudit") return "audit";
  return "organization";
}

export function canManageSettings(user: SessionUser): boolean {
  return hasCapability(user, "settings.manage");
}
