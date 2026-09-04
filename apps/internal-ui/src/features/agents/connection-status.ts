import type { StatusPillKey } from "../../shared/ui";

/** Состояние подключения приходит строкой — на экран идёт словарь, не энум. */
const CONNECTION_STATUS: Record<string, StatusPillKey> = {
  OK: "healthy",
  ERROR: "error",
  PENDING: "pending",
  UNCHECKED: "unchecked",
};

export function connectionStatus(status: string): StatusPillKey {
  return CONNECTION_STATUS[status] ?? "unchecked";
}
