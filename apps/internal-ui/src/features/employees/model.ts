import { shortDateYear } from "../../shared/utils";
import type { Employee, EmployeeAuditEvent, Role } from "../../types";
import { t } from "../../i18n";

export type EmployeeStatus = "active" | "blocked" | "invited";
export type EmployeeRoleFilter = "all" | Role;

export type EmployeeForm = {
  email: string;
  fullName: string;
  phone: string;
  positionTitle: string;
  role: Role;
  groupIds: number[];
  totpEnabled: boolean;
};

const AUDIT_LABELS: Record<string, string> = {
  "identity.employee_blocked": t("admin.operator_blocked"),
  "identity.employee_created": t("admin.operator_created"),
  "identity.employee_password_reset": t("admin.operator_password_reset"),
  "identity.employee_groups_changed": t("admin.operator_groups_changed"),
  "identity.employee_role_changed": t("admin.system_role_changed"),
  "identity.employee_sessions_terminated": t("admin.active_sessions_ended"),
  "identity.employee_unblocked": t("admin.operator_unblocked"),
  "identity.employee_updated": t("admin.operator_details_changed"),
  "identity.ownership_transferred": t("admin.organization_ownership_transferred"),
};

// Бейджи роли и статуса (дизайн-базлайн v2, «Сотрудники Baseline», таблицы
// ROLE и STATUS): владелец — акцентом, администратор — цветом AI, сотрудник —
// нейтральный; статус — полутон своего цвета с точкой.
const ROLE_BADGE: Record<Role, { text: string; bg: string; color: string }> = {
  OWNER: { text: t("common.owner"), bg: "var(--primary-bg)", color: "var(--primary-text)" },
  ADMIN: { text: t("common.administrator"), bg: "color-mix(in srgb, var(--ai) 14%, var(--surface-card))", color: "var(--ai)" },
  EMPLOYEE: { text: t("common.operator"), bg: "var(--n-9)", color: "var(--n-3)" },
};

const STATUS_BADGE: Record<EmployeeStatus, { text: string; bg: string; color: string }> = {
  active: { text: t("shared.active"), bg: "var(--success-bg)", color: "var(--success-text)" },
  invited: { text: t("shared.invited"), bg: "var(--warning-bg)", color: "var(--warning-text)" },
  blocked: { text: t("shared.blocked"), bg: "var(--error-bg)", color: "var(--error-text)" },
};

// Цвет аватара без фото — по порядку сотрудников, как в касте дизайн-базлайна;
// у заблокированного серый (кадр E1).
const AVATAR_PALETTE = ["#c4456b", "#4c6ef0", "#3b82c4", "#13a8a8", "#d4860b"];

export function employeeAvatarColor(employee: Employee): string {
  if (employee.isBlocked) return "#8c8c8c";
  return AVATAR_PALETTE[(employee.id - 1) % AVATAR_PALETTE.length];
}

export function roleBadge(role: Role) {
  return ROLE_BADGE[role];
}

export function statusBadge(employee: Employee) {
  return STATUS_BADGE[employeeStatusKey(employee)];
}

export function employeeStatusKey(employee: Employee): EmployeeStatus {
  if (employee.isBlocked) return "blocked";
  if (employee.mustChangePassword) return "invited";
  return "active";
}


export function employeeForm(employee: Employee): EmployeeForm {
  return {
    fullName: employee.fullName || employee.email,
    phone: employee.phone || "",
    email: employee.email,
    positionTitle: employee.positionTitle,
    role: employee.role,
    groupIds: employee.groups.map((group) => group.id),
    totpEnabled: employee.totpEnabled,
  };
}

export function groupsLabel(employee: Employee) {
  if (!employee.groups.length) return t("common.no_group");
  return employee.groups.map((group) => group.name).join(", ");
}

export function roleAccessLabel(employee: Employee) {
  if (employee.role === "OWNER" || employee.role === "ADMIN") return t("common.full_access");
  return t("admin.chat_only");
}

export function formatDate(value?: string | null, empty = "—") {
  if (!value) return empty;
  return shortDateYear(value) || empty;
}

export function formatLastLogin(value?: string | null, empty = t("admin.never_signed")) {
  if (!value) return empty;
  const elapsed = Date.now() - new Date(value).getTime();
  if (elapsed < 0 || elapsed >= 7 * 24 * 60 * 60 * 1000) return formatDate(value, empty);
  const minutes = Math.floor(elapsed / 60_000);
  if (minutes < 1) return t("common.just_now");
  if (minutes < 60) return t("time.minutes_ago", { count: minutes });
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return t("time.hours_ago", { count: hours });
  return t("time.days_ago", { count: Math.floor(hours / 24) });
}

export function auditItem(event: EmployeeAuditEvent) {
  return {
    code: event.action,
    dot: event.result === "DENIED" ? "var(--error)" : "var(--primary)",
    text: AUDIT_LABELS[event.action] ?? event.action,
    time: formatLastLogin(event.createdAt, "—"),
  };
}
