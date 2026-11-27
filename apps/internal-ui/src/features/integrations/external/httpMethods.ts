const BODY_METHODS = ["POST", "PUT", "PATCH", "DELETE"] as const;
export const HTTP_METHODS = ["GET", ...BODY_METHODS, "HEAD", "OPTIONS"] as const;
export type HttpMethod = typeof HTTP_METHODS[number];

export function hasRequestBody(method?: string): boolean {
  return BODY_METHODS.some(item => item === method);
}
