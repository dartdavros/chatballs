import { api, ApiError } from "../../../api/client";
import { t } from "../../../i18n";
import type { OAuthState, ServiceAdapter, ServiceConnection, ServiceFailure } from "./types";

const BASE = "/api/v1/integrations";

type Values = Record<string, unknown>;

export type ConnectBody = { adapter: string; authMethod: string; name: string; values: Values };

export function fetchAdapters(): Promise<ServiceAdapter[]> {
  return api<{ items: ServiceAdapter[] }>(`${BASE}/service-adapters/`).then((body) => body.items);
}

export function fetchConnections(): Promise<ServiceConnection[]> {
  return api<{ items: ServiceConnection[] }>(`${BASE}/services/`).then((body) => body.items);
}

export function fetchConnection(id: number): Promise<ServiceConnection> {
  return api<{ connection: ServiceConnection }>(`${BASE}/services/${id}/`).then((body) => body.connection);
}

export function createConnection(body: ConnectBody): Promise<ServiceConnection> {
  return api<{ connection: ServiceConnection }>(`${BASE}/services/`, { method: "POST", body: JSON.stringify(body) })
    .then((response) => response.connection);
}

export function updateConnection(id: number, patch: { name?: string; isActive?: boolean }): Promise<ServiceConnection> {
  return api<{ connection: ServiceConnection }>(`${BASE}/services/${id}/`, { method: "PATCH", body: JSON.stringify(patch) })
    .then((response) => response.connection);
}

export function deleteConnection(id: number): Promise<void> {
  return api(`${BASE}/services/${id}/`, { method: "DELETE" });
}

export function checkConnection(id: number, inputs?: Values): Promise<ServiceConnection> {
  return api<{ connection: ServiceConnection }>(`${BASE}/services/${id}/check/`, { method: "POST", body: JSON.stringify({ inputs }) })
    .then((response) => response.connection);
}

export function replaceAccess(id: number, values: Values): Promise<ServiceConnection> {
  return api<{ connection: ServiceConnection }>(`${BASE}/services/${id}/access/`, { method: "POST", body: JSON.stringify({ values }) })
    .then((response) => response.connection);
}

export function startOAuth(body: ConnectBody & { connectionId?: number }): Promise<{ state: OAuthState; authorizeUrl: string }> {
  return api(`${BASE}/services/oauth/start/`, { method: "POST", body: JSON.stringify(body) });
}

export function fetchOAuthState(id: string): Promise<OAuthState> {
  return api<{ state: OAuthState }>(`${BASE}/services/oauth/${id}/`).then((body) => body.state);
}

/** Разобрать отказ API: ошибки полей, причину проверки или общий текст. */
export function serviceFailure(error: unknown): ServiceFailure {
  const payload = error instanceof ApiError && error.payload && typeof error.payload === "object" ? error.payload as Record<string, unknown> : {};
  const errors = (payload.errors ?? {}) as Record<string, string[]>;
  const fields = Object.fromEntries(Object.entries(errors).map(([name, messages]) => [name, messages[0] ?? ""]));
  const failure = payload.error as ServiceFailure["error"] | undefined;
  return { fields, error: failure ?? null, message: failure || Object.keys(fields).length ? "" : t("services.request_failed") };
}
