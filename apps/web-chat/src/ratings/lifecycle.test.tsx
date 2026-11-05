import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { applyWidgetLanguage } from "../i18n";
import type { RatingRequest } from "./api";
import { RatingOutcome } from "./RatingOutcome";
import { RatingRequestCard } from "./RatingRequestCard";
import type { useRating } from "./useRating";

const request: RatingRequest = {
  credential: "test-credential",
  text: "Question",
  scale: [1, 2, 3, 4, 5].map(value => ({ value, label: String(value) })),
  expiresAt: null,
  presentation: { name: "Company", accent: "#1677ff", siteUrl: "https://example.test", conversationDate: "2020-01-01", language: "ru" },
};

describe("WEB rating lifecycle contract", () => {
  it("keeps both timeless and previously delivered offers actionable", () => {
    const timeless = renderToStaticMarkup(<RatingRequestCard request={request} />);
    const legacy = renderToStaticMarkup(<RatingRequestCard request={{ ...request, expiresAt: "2020-01-08T00:00:00Z" }} />);
    expect(timeless).toBe(legacy);
    expect(timeless.match(/<button/g)).toHaveLength(5);
    expect(timeless).not.toContain("disabled");
    expect(timeless).not.toContain(request.credential);
  });

  it("uses the existing localized unavailable outcome without a time-expiry claim", () => {
    const rating = { state: "unavailable", presentation: request.presentation } as ReturnType<typeof useRating>;
    applyWidgetLanguage("ru");
    const ru = renderToStaticMarkup(<RatingOutcome rating={rating} />);
    expect(ru).toContain("Ссылка больше не действует");
    expect(ru).toContain("Оценить этот разговор уже нельзя");
    applyWidgetLanguage("en");
    const en = renderToStaticMarkup(<RatingOutcome rating={rating} />);
    expect(en).toContain("This link is no longer valid");
    expect(en).toContain("This conversation can no longer be rated");
    applyWidgetLanguage("ru");
  });
});
