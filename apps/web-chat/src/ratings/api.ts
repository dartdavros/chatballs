export type RatingChoice = { value: number; label: string };
export type RatingPresentation = { name: string; accent: string; siteUrl: string; conversationDate: string; language: string };
export type RatingRequest = { credential: string; text: string; scale: RatingChoice[]; expiresAt: string | null; presentation: RatingPresentation };
export type RatingResult = { value: number; comment: string; receivedAt: string };
export type RatingQuestion = Omit<RatingRequest, "credential"> & { commentMaxLength: number; result: RatingResult | null };

export class RatingError extends Error {
  constructor(public status: number) { super(`rating:${status}`); }
}
export async function ratingApi<T>(credential: string, data?: { value: number; comment: string }): Promise<T> {
  const response = await fetch("/api/v1/ratings/", {
    method: data ? "POST" : "GET", credentials: "omit", cache: "no-store", referrerPolicy: "no-referrer",
    headers: { Authorization: `Bearer ${credential}`, ...(data ? { "Content-Type": "application/json" } : {}) },
    body: data ? JSON.stringify(data) : undefined,
  });
  if (!response.ok) throw new RatingError(response.status);
  return response.json() as Promise<T>;
}
