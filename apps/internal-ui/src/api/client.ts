const configuredApiBase = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");
let activeOrganizationPublicId: string | null = null;

// Имя CSRF-cookie должно совпадать с backend CSRF_COOKIE_NAME (settings_app):
// secure-режим (https) → "__Host-custocrm-app-csrf", dev по http → fallback-имя
// (CSRF_COOKIE_SECURE выключен, префикс __Host- недоступен без Secure).
const CSRF_COOKIE_NAME =
  typeof window !== "undefined" && window.location.protocol === "https:" ? "__Host-custocrm-app-csrf" : "custocrm_app_csrftoken";

const tenantNamespaces = [
  "access-profiles",
  "ai",
  "calls",
  "channels",
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
    super(payload.detail ?? "Ошибка запроса");
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

function resolveApiUrl(path: string): string {
  path = organizationScopedPath(path);
  if (!configuredApiBase) return path;
  if (configuredApiBase.endsWith("/api/v1") && path.startsWith("/api/v1/")) {
    return `${configuredApiBase}${path.slice("/api/v1".length)}`;
  }
  return `${configuredApiBase}${path}`;
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
    const payload = await response.json().catch(() => ({ detail: "Ошибка запроса" })) as ApiErrorPayload;
    throw new ApiError(response.status, payload);
  }
  if (response.status === 204 || response.status === 205) return undefined as T;
  return response.json() as Promise<T>;
}

// Multipart-загрузка (вложения знаний): Content-Type выставляет браузер (boundary).
export async function apiUpload<T>(path: string, form: FormData): Promise<T> {
  const headers = new Headers({ Accept: "application/json", "X-CSRFToken": getCookie(CSRF_COOKIE_NAME) });
  const response = await fetch(resolveApiUrl(path), { method: "POST", body: form, credentials: "include", headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Ошибка запроса" })) as ApiErrorPayload;
    throw new ApiError(response.status, payload);
  }
  return response.json() as Promise<T>;
}
