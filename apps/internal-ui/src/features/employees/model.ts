import type { Employee, EmployeeAuditEvent, Role } from "../../types";

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
  "identity.employee_blocked": "Сотрудник заблокирован",
  "identity.employee_created": "Сотрудник создан",
  "identity.employee_password_reset": "Пароль сотрудника сброшен",
  "identity.employee_groups_changed": "Изменены группы сотрудника",
  "identity.employee_role_changed": "Изменена системная роль",
  "identity.employee_sessions_terminated": "Активные сессии завершены",
  "identity.employee_unblocked": "Сотрудник разблокирован",
  "identity.employee_updated": "Данные сотрудника изменены",
  "identity.ownership_transferred": "Передано владение организацией",
};

export function employeeStatusKey(employee: Employee): EmployeeStatus {
  if (employee.isBlocked) return "blocked";
  if (employee.mustChangePassword) return "invited";
  return "active";
}

export function filterEmployees(
  employees: Employee[],
  role: EmployeeRoleFilter,
  groupId: number | "all",
  query: string,
) {
  const q = query.trim().toLowerCase();
  return employees.filter((employee) => (
    (role === "all" || employee.role === role)
    && (groupId === "all" || employee.groups.some((group) => group.id === groupId))
    && (!q
      || employee.fullName.toLowerCase().includes(q)
      || employee.email.toLowerCase().includes(q)
      || employee.positionTitle.toLowerCase().includes(q))
  ));
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
  if (!employee.groups.length) return "Без группы";
  return employee.groups.map((group) => group.name).join(", ");
}

export function roleAccessLabel(employee: Employee) {
  if (employee.role === "OWNER" || employee.role === "ADMIN") return "Полный доступ";
  return "Только чат";
}

export function formatDate(value?: string | null, empty = "—") {
  if (!value) return empty;
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value)).replace(/\s?г\.$/u, "");
}

export function formatLastLogin(value?: string | null, empty = "не входил") {
  if (!value) return empty;
  const elapsed = Date.now() - new Date(value).getTime();
  if (elapsed < 0 || elapsed >= 7 * 24 * 60 * 60 * 1000) return formatDate(value, empty);
  const minutes = Math.floor(elapsed / 60_000);
  if (minutes < 1) return "сейчас";
  if (minutes < 60) return `${minutes} мин назад`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} ч назад`;
  return `${Math.floor(hours / 24)} дн. назад`;
}

export function auditItem(event: EmployeeAuditEvent) {
  return {
    code: event.action,
    dot: event.result === "DENIED" ? "var(--error)" : "var(--primary)",
    text: AUDIT_LABELS[event.action] ?? event.action,
    time: formatLastLogin(event.createdAt, "—"),
  };
}
