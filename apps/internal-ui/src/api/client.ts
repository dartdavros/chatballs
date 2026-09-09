import { t } from "../i18n";

const configuredApiBase = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");
let activeOrganizationPublicId: string | null = null;

// Имя CSRF-cookie должно совпадать с backend CSRF_COOKIE_NAME (settings_app):
// secure-режим (https) → "__Host-chatballs-app-csrf", dev по http → fallback-имя
// (CSRF_COOKIE_SECURE выключен, префикс __Host- недоступен без Secure).
const CSRF_COOKIE_NAME =
  typeof window !== "undefined" && window.location.protocol === "https:" ? "__Host-chatballs-app-csrf" : "chatballs_app_csrftoken";

const tenantNamespaces = [
  "agents",
  "ai",
  "calls",
  "company",
  "conversations",
  "employees",
  "integrations",
  "notifications",
  "support",
];

const publicPaths = [
  "/api/v1/ai/files/",
  "/api/v1/calls/access/",
  "/api/v1/calls/invites/",
  "/api/v1/support/sessions/",
  "/api/v1/help/",
];

export type ApiErrorPayload = {
  detail?: string;
  [key: string]: unknown;
};

export class ApiError<TPayload extends { detail?: string } = ApiErrorPayload> extends Error {
  readonly status: number;
  readonly payload: TPayload;

  constructor(status: number, payload: TPayload) {
    super(payload.detail ?? t("common.request_failed"));
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

export function setActiveOrganization(publicId: string | null): void {
  activeOrganizationPublicId = publicId;
}

function organizationScopedPath(path: string): string {
  if (!path.startsWith("/api/v1/") || publicPaths.some((item) => path.startsWith(item))) {
    return path;
  }
  const namespace = path.slice("/api/v1/".length).split("/", 1)[0];
  if (!tenantNamespaces.includes(namespace)) return path;
  if (!activeOrganizationPublicId) {
    throw new Error("Organization context is required");
  }
  return `/api/v1/organizations/${activeOrganizationPublicId}${path.slice("/api/v1".length)}`;
}

export function resolveApiUrl(path: string): string {
  path = organizationScopedPath(path);
  if (!configuredApiBase) return path;
  if (configuredApiBase.endsWith("/api/v1") && path.startsWith("/api/v1/")) {
    return `${configuredApiBase}${path.slice("/api/v1".length)}`;
  }
  return `${configuredApiBase}${path}`;
}

/** Адрес WebSocket-канала организации: та же схема адресов, что у REST, и та
 *  же сессия. Без активной организации канала нет — вернётся null. */
export function resolveWebSocketUrl(path: string): string | null {
  if (typeof window === "undefined" || !activeOrganizationPublicId) return null;
  const base = configuredApiBase
    ? new URL(configuredApiBase, window.location.origin)
    : new URL(window.location.origin);
  const protocol = base.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${base.host}/ws/organizations/${activeOrganizationPublicId}${path}`;
}

function getCookie(name: string): string {
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`));
  return cookie ? decodeURIComponent(cookie.split("=")[1]) : "";
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = init.method ?? "GET";
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (method !== "GET") {
    headers.set("Content-Type", "application/json");
    headers.set("X-CSRFToken", getCookie(CSRF_COOKIE_NAME));
  }
  const response = await fetch(resolveApiUrl(path), {
    ...init,
    credentials: "include",
    headers,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: t("common.request_failed") })) as ApiErrorPayload;
    throw new ApiError(response.status, payload);
  }
  if (response.status === 204 || response.status === 205) return undefined as T;
  return response.json() as Promise<T>;
}

// Multipart-загрузка (вложения знаний, файлы статей портала): Content-Type
// выставляет браузер (boundary). На XHR, а не на fetch, потому что прогресс
// отправки нужен рейке файлов редактора статьи (кадр PT8) — у fetch его нет.
export function apiUpload<T>(path: string, form: FormData, onProgress?: (percent: number) => void): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", resolveApiUrl(path));
    request.withCredentials = true;
    request.setRequestHeader("Accept", "application/json");
    request.setRequestHeader("X-CSRFToken", getCookie(CSRF_COOKIE_NAME));
    if (onProgress) {
      request.upload.onprogress = (event) => {
        if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
      };
    }
    request.onerror = () => reject(new ApiError(0, { detail: t("shared.network_error") }));
    request.onload = () => {
      let payload: unknown = null;
      try {
        payload = request.responseText ? JSON.parse(request.responseText) : null;
      } catch {
        payload = null;
      }
      if (request.status >= 200 && request.status < 300) {
        resolve(payload as T);
        return;
      }
      reject(new ApiError(request.status, (payload ?? { detail: t("common.request_failed") }) as ApiErrorPayload));
    };
    request.send(form);
  });
}
