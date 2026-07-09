const configuredApiBase = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");

function resolveApiUrl(path: string): string {
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
    headers.set("X-CSRFToken", getCookie("csrftoken"));
  }
  const response = await fetch(resolveApiUrl(path), {
    ...init,
    credentials: "include",
    headers,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Ошибка запроса" }));
    throw new Error(payload.detail ?? "Ошибка запроса");
  }
  if (response.status === 204 || response.status === 205) return undefined as T;
  return response.json() as Promise<T>;
}
