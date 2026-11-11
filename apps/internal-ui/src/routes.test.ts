import { setCurrentLanguage } from "@chatballs/shared";
import { afterEach, describe, expect, it } from "vitest";

import { t } from "./i18n";
import { routeFromPath } from "./router";
import { routeTitle, routes } from "./routes";
import { documentTitle } from "./shared/useDocumentTitle";

afterEach(() => { setCurrentLanguage("ru"); });

describe("workspace document titles", () => {
  it("names the chats tab separately from the unchanged sidebar label", () => {
    setCurrentLanguage("ru");
    expect(documentTitle(routeTitle("chat"))).toBe("Чаты · Chatballs");
    expect(t("common.chat")).toBe("Чат");
    setCurrentLanguage("en");
    expect(documentTitle(routeTitle("chat"))).toBe("Chats · Chatballs");
    expect(t("common.chat")).toBe("Chat");
  });

  it("resolves names at render time for every route on both languages", () => {
    for (const language of ["ru", "en"]) {
      setCurrentLanguage(language);
      for (const route of Object.keys(routes) as Array<keyof typeof routes>) {
        expect(routeTitle(route)).not.toMatch(/^(navigation|common|page_titles|shared|scenarios)\./);
        expect(routeTitle(route).length).toBeGreaterThan(0);
        expect(documentTitle(routeTitle(route))).toMatch(/ · Chatballs$/);
      }
    }
  });

  it("uses the same route title for a direct URL and restored history entries", () => {
    setCurrentLanguage("ru");
    const titles = ["/chat", "/scenarios?scenario=demo", "/widgets", "/chat"].map(path => {
      const url = new URL(path, "https://example.test");
      return documentTitle(routeTitle(routeFromPath(url.pathname, url.search).route));
    });
    expect(titles).toEqual(["Чаты · Chatballs", "Сценарии · Chatballs", "Виджеты · Chatballs", "Чаты · Chatballs"]);
  });

  it("keeps the product title as the empty section fallback", () => {
    expect(documentTitle("")).toBe("Chatballs");
  });
});
