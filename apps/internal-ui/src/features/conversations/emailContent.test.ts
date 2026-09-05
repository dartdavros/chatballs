import { describe, expect, it } from "vitest";

import { foldQuotedHtml, splitQuotedEmail } from "./emailContent";

describe("splitQuotedEmail", () => {
  it("preserves a message without quoted history", () => {
    expect(splitQuotedEmail("Первая строка\n\nВторая строка")).toEqual({
      latest: "Первая строка\n\nВторая строка",
      quoted: "",
    });
  });

  it("separates lines prefixed as an email quote", () => {
    expect(splitQuotedEmail("Новый ответ\n\n> Старое письмо\n> Вторая строка")).toEqual({
      latest: "Новый ответ",
      quoted: "> Старое письмо\n> Вторая строка",
    });
  });

  it("separates an inline localized reply header", () => {
    const text = "Держись\nСр, 22 июля 2026 г. в 21:10, Foxray <foxray@example.com>: > Старое письмо";
    expect(splitQuotedEmail(text)).toEqual({
      latest: "Держись",
      quoted: "Ср, 22 июля 2026 г. в 21:10, Foxray <foxray@example.com>: > Старое письмо",
    });
  });
});

describe("foldQuotedHtml", () => {
  it("wraps an HTML quote in a native collapsed section", () => {
    expect(foldQuotedHtml("<p>Ответ</p><blockquote>История</blockquote>")).toBe(
      '<p>Ответ</p><details class="email-quoted"><summary>Показать предыдущие сообщения</summary><blockquote>История</blockquote></details>',
    );
  });

  it("does not change HTML without a quote", () => {
    expect(foldQuotedHtml("<p>Ответ</p>")).toBe("<p>Ответ</p>");
  });
});
