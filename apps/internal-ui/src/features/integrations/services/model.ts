import { fmt, t, tn } from "../../../i18n";
import type { StatusPillKey } from "../../../shared/ui";
import type { ServiceAdapter, ServiceAuthMethod, ServiceConnection } from "./types";

const ACCESS_FAILURES = new Set(["unauthorized", "forbidden", "access_expired", "access_revoked", "invalid_link", "crm_access_missing"]);

// Одобрено владельцем: ошибка сети не означает отзыв/истечение доступа.
// Причина проверки уже локализована сервером; новых текстов/баннеров нет.
export function checkFailureMessage(connection: ServiceConnection) {
  return connection.status === "lost" && connection.error && !ACCESS_FAILURES.has(connection.error.code) ? connection.error : null;
}

// Отметка состояния подключения (кадры «Список» и «Карточка» Сервисы.dc.html).
// «Приостановлено» — одобренное владельцем дополнение к макету.
export function connectionBadge(connection: ServiceConnection): { status: StatusPillKey; label: string } {
  if (!connection.isActive) return { status: "unchecked", label: t("services.status_paused") };
  if (connection.status === "ok") return { status: "healthy", label: t("services.status_ok") };
  if (connection.status === "lost") return { status: "error", label: t("services.status_lost") };
  return { status: "unchecked", label: t("services.status_unchecked") };
}

export function scenariosLabel(connection: ServiceConnection): string {
  const enabled = connection.scenarios.enabled;
  if (enabled > 0 && (connection.status === "lost" || !connection.isActive)) return t("services.scenarios_paused");
  return enabled > 0 ? tn("services.scenarios_enabled", enabled) : t("services.scenarios_none");
}

export function connectionsOf(adapter: ServiceAdapter, connections: ServiceConnection[]): number {
  return connections.filter((item) => item.adapter === adapter.key).length;
}

export function authMethodOf(adapter: ServiceAdapter | undefined, connection: ServiceConnection): ServiceAuthMethod | undefined {
  return adapter?.authMethods.find((method) => method.key === connection.authMethod);
}

function checkedWhen(value: string): string {
  const date = new Date(value);
  const today = new Date();
  const sameDay = date.toDateString() === today.toDateString();
  return sameDay ? t("services.when_today") : fmt.shortDateTime(value);
}

/** Строка под «Доступ · …» в блоке «Подключение». */
export function accessState(connection: ServiceConnection, method: ServiceAuthMethod | undefined): string {
  if (connection.status === "lost") return checkFailureMessage(connection)?.title ?? t("services.state_lost");
  if (connection.status === "unchecked" || !connection.lastCheckedAt) return t("services.state_unchecked");
  const when = checkedWhen(connection.lastCheckedAt);
  return method?.savedLabel
    ? t("services.state_saved_checked", { saved: method.savedLabel, when })
    : t("services.state_checked", { when });
}

export function adapterOf(adapters: ServiceAdapter[], connection: ServiceConnection | null): ServiceAdapter | undefined {
  return connection ? adapters.find((adapter) => adapter.key === connection.adapter) : undefined;
}
