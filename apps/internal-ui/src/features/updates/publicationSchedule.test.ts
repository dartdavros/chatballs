import { describe, expect, it } from "vitest";
import { nextPublicationBoundary, publicationIsActive } from "./publicationSchedule";

describe("publication window", () => {
  const message = { starts_at: "2026-11-22T10:00:00+03:00", ends_at: "2026-11-22T18:00:00+03:00" };
  const start = Date.parse(message.starts_at);
  const end = Date.parse(message.ends_at);

  it("starts at the lower boundary and stops at the upper boundary", () => {
    expect(publicationIsActive(message, start - 1)).toBe(false);
    expect(publicationIsActive(message, start)).toBe(true);
    expect(publicationIsActive(message, end - 1)).toBe(true);
    expect(publicationIsActive(message, end)).toBe(false);
  });

  it("schedules both transitions without requiring a new server response", () => {
    expect(nextPublicationBoundary([message], start - 1000)).toBe(1000);
    expect(nextPublicationBoundary([message], start)).toBe(end - start);
    expect(nextPublicationBoundary([message], end)).toBeNull();
  });

  it("retains the legacy response while rejecting incomplete windows", () => {
    expect(publicationIsActive({}, start)).toBe(true);
    expect(publicationIsActive({ starts_at: message.starts_at }, start)).toBe(false);
  });
});
