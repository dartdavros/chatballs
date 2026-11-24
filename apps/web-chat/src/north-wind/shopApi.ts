const ROOT = "/api/v1/demo-local/storefront/";

export class ShopRequestError extends Error {
  constructor(readonly code: string, readonly status: number) {
    super(code);
  }
}

export function storefrontApi(token: string) {
  return async function request<T>(operation: string, values?: Record<string, unknown>, idempotencyKey?: string): Promise<T> {
    const headers = new Headers({"Authorization": `Bearer ${token}`, "Accept": "application/json"});
    if (values) headers.set("Content-Type", "application/json");
    if (idempotencyKey) headers.set("Idempotency-Key", idempotencyKey);
    const response = await fetch(`${ROOT}${operation}/`, {
      method: values ? "POST" : "GET",
      headers,
      body: values ? JSON.stringify(values) : undefined,
      credentials: operation === "start" ? "same-origin" : "omit",
      cache: "no-store",
      redirect: "error",
    });
    const payload = await response.json();
    if (!response.ok) throw new ShopRequestError(payload.code ?? "unavailable", response.status);
    return payload as T;
  };
}
