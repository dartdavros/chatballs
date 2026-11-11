import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import articleYaml from "./articles/instrumenty-agenta.yml?raw";
import plan from "./chatballs.json";
import { parseArticleYaml } from "../../apps/internal-ui/src/features/support-portals/parseArticleYaml";
import { MarkdownContent, parseMarkdown } from "../../apps/internal-ui/src/features/help-center/MarkdownContent";
import { ServerWarning } from "../../apps/internal-ui/src/features/integrations/external/ServerWarning";
import { helpArticleUrl } from "../../apps/internal-ui/src/shared/help";

const { articles } = parseArticleYaml(articleYaml);

describe("agent tools help article", () => {
  it("imports Russian and English revisions of the same article", () => {
    expect(articles.map((a) => [a.locale, a.slug, a.title, a.categoryPath])).toEqual([
      ["ru", "instrumenty-agenta", "Инструменты агента", ["ИИ-агенты"]],
      ["en", "instrumenty-agenta", "Agent tools", ["ИИ-агенты"]],
    ]);
    for (const article of articles) {
      const html = renderToStaticMarkup(createElement(MarkdownContent, { content: article.content }));
      expect(html).toContain("<ol>");
      expect(html).toContain("https://shop.example.ru/mcp");
      expect(html).toContain("https://shop.example.ru/api/orders/{order_number}");
      expect(html).toContain("get_order_status");
      expect(html).toContain("10482");
      expect(html).toContain("10483");
      expect(html).toContain("/articles/kartochka-agenta");
      const headings = parseMarkdown(article.content).headings;
      expect(headings).toHaveLength(6);
      expect(headings[0].title).toMatch(/MCP/);
      expect(headings[1].title).toMatch(/MCP/);
      expect(headings[2].title).toMatch(/HTTP/);
      expect(headings[4].title).toMatch(/подменяемы|tampered/);
      expect(html).toContain("https://mcp-test.chatballs.ru/mcp");
      for (const name of ["search_products", "get_product", "get_order_status", "get_delivery_options"]) {
        expect(html).toContain(name);
      }
      expect(html).toContain("DEMO-P001");
      expect(html).toContain("DEMO-1001");
    }
    expect(articles[0].content).toContain("API вашей организации должен сам проверять, что заказ принадлежит этому клиенту, при каждом запросе");
    expect(articles[1].content).toContain("API must itself check that the order belongs to this customer on every request");
  });

  it("links the server warning and editorial map to the importable article", () => {
    const article = articles[0];
    const html = renderToStaticMarkup(createElement(ServerWarning));
    expect(html).toContain(`href="${helpArticleUrl(article.slug)}"`);
    expect(html).toContain('class="link"');
    expect(html).toContain('rel="noopener noreferrer"');
    expect(plan.order.agents).toContain(article.slug);
    expect(Object.values(plan.order).flat().filter((slug) => slug === article.slug)).toHaveLength(1);
    expect(plan.related["kartochka-agenta"]).toContain(article.slug);
    expect(plan.related["instrumenty-agenta"]).toContain("kartochka-agenta");
  });
});
