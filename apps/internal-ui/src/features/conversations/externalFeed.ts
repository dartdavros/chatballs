import type { ExternalNotice } from "./apiTypes";

export function withExternalNotices<T extends { key: string; createdAt: string }>(rows: readonly T[], notices: readonly ExternalNotice[], hasOlder: boolean) {
  const floor = hasOlder && rows.length ? Date.parse(rows[0].createdAt) : -Infinity;
  const extra = notices.filter(notice => Date.parse(notice.createdAt) >= floor).map(notice => ({
    kind: "external_notice" as const, key: `external:${notice.id}`, createdAt: notice.createdAt, notice,
  }));
  return [...rows, ...extra].sort((a, b) => Date.parse(a.createdAt) - Date.parse(b.createdAt));
}
