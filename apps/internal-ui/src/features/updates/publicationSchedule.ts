export type PublicationWindow = { starts_at?: string; ends_at?: string };

export function publicationIsActive(item: PublicationWindow, now: number): boolean {
  if (item.starts_at === undefined && item.ends_at === undefined) return true;
  return Date.parse(item.starts_at ?? "") <= now && now < Date.parse(item.ends_at ?? "");
}

export function nextPublicationBoundary(items: PublicationWindow[], now: number): number | null {
  const future = items.flatMap((item) => [Date.parse(item.starts_at ?? ""), Date.parse(item.ends_at ?? "")])
    .filter((time) => Number.isFinite(time) && time > now);
  return future.length ? Math.min(...future) - now : null;
}
