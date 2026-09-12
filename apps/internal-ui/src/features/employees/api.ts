import { api } from "../../api/client";
import type { PagedPayload } from "../../shared/usePagedResource";
import type { Employee, EmployeeInvitation, Role } from "../../types";
import type { EmployeeRoleFilter } from "./model";

// Действия над сотрудником (дизайн-базлайн v2, кадры E2, E3, E5–E8).
// Пароль первичного доступа сервер отдаёт ровно один раз — открытым он нигде
// не хранится, поэтому ответ показывается сразу в диалоге.

export type PasswordMode = "mail" | "show";

export type IssuedPassword = {
  employee: Employee;
  password: string;
  reason: "created" | "reset";
};

export type EmployeeCreateInput = {
  fullName: string;
  phone: string;
  email: string;
  role: Role;
  positionTitle: string;
  groupIds: number[];
  passwordMode: PasswordMode;
};

export async function createEmployee(input: EmployeeCreateInput): Promise<IssuedPassword | null> {
  // Если адрес уже принадлежит учётной записи из другой организации, сервер
  // вместо сотрудника выписывает приглашение: employee и password пусты,
  // человек появится в списке после того, как примет его.
  const payload = await api<{ employee: Employee | null; password: string | null; invited?: boolean }>("/api/v1/employees/operators/", {
    method: "POST",
    body: JSON.stringify(input),
  });
  return payload.password && payload.employee
    ? { employee: payload.employee, password: payload.password, reason: "created" }
    : null;
}

export async function resetEmployeePassword(userId: number, mode: PasswordMode): Promise<IssuedPassword | null> {
  const payload = await api<{ employee: Employee; password: string | null }>(`/api/v1/employees/${userId}/reset-password/`, {
    method: "POST",
    body: JSON.stringify({ mode }),
  });
  return payload.password ? { employee: payload.employee, password: payload.password, reason: "reset" } : null;
}

export async function terminateEmployeeSessions(userId: number): Promise<void> {
  await api(`/api/v1/employees/${userId}/revoke-sessions/`, { method: "POST" });
}

export async function blockEmployee(userId: number, block: boolean): Promise<void> {
  await api(`/api/v1/employees/${userId}/${block ? "block" : "unblock"}/`, { method: "POST" });
}

// Список сотрудников: страница, роль, группа и поиск считает сервер (кадры E1/E2).
export type EmployeeListQuery = {
  role: EmployeeRoleFilter;
  groupId: number | "all";
  query: string;
};

// Вместе со страницей сервер отдаёт ожидающие приглашения — их мало и они
// не листаются.
export type EmployeesPayload = PagedPayload<Employee> & { invitations?: EmployeeInvitation[] };

export function fetchEmployees(
  { role, groupId, query }: EmployeeListQuery,
  page: number,
): Promise<EmployeesPayload> {
  const params = new URLSearchParams({ page: String(page) });
  if (role !== "all") params.set("role", role);
  if (groupId !== "all") params.set("group", String(groupId));
  if (query.trim()) params.set("q", query.trim());
  return api<EmployeesPayload>(`/api/v1/employees/?${params.toString()}`);
}

export async function resendInvitation(invitationId: number): Promise<void> {
  await api(`/api/v1/employees/invitations/${invitationId}/resend/`, { method: "POST" });
}

export async function revokeInvitation(invitationId: number): Promise<void> {
  await api(`/api/v1/employees/invitations/${invitationId}/revoke/`, { method: "POST" });
}

/** Кандидаты на владение (кадр E9) — только действующие администраторы.
 *  Роль и поиск отбирает сервер; если админов больше страницы, у выбора
 *  появляется строка поиска. */
export function fetchOwnershipCandidates(query = ""): Promise<PagedPayload<Employee>> {
  const params = new URLSearchParams({ role: "ADMIN", pageSize: "100" });
  if (query.trim()) params.set("q", query.trim());
  return api<PagedPayload<Employee>>(`/api/v1/employees/?${params.toString()}`);
}

export function fetchOwner(): Promise<PagedPayload<Employee>> {
  return api<PagedPayload<Employee>>("/api/v1/employees/?role=OWNER");
}
