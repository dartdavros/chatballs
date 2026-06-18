const API_BASE = "http://localhost:8010";

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
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Ошибка запроса" }));
    throw new Error(payload.detail ?? "Ошибка запроса");
  }
  return response.json() as Promise<T>;
}
