import { api } from "../../api/client";
import type { Employee, Role } from "../../types";

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
  const payload = await api<{ employee: Employee; password: string | null }>("/api/v1/employees/operators/", {
    method: "POST",
    body: JSON.stringify(input),
  });
  return payload.password ? { employee: payload.employee, password: payload.password, reason: "created" } : null;
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
