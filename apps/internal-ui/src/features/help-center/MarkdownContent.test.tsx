import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { MarkdownContent, parseMarkdown } from "./MarkdownContent";

describe("parseMarkdown", () => {
  it("creates stable unique ids for repeated headings", () => {
    const result = parseMarkdown("## Установка\n\nТекст\n\n## Установка");
    expect(result.headings.map((heading) => heading.id)).toEqual([
      "установка",
      "установка-2",
    ]);
  });

  it("keeps code fences out of paragraphs", () => {
    const result = parseMarkdown("До\n\n```sh\necho ok\n```\n\nПосле");
    expect(result.blocks.map((block) => block.kind)).toEqual([
      "paragraph",
      "code",
      "paragraph",
    ]);
  });

  it("renders GFM tables, quotes and task lists", () => {
    const html = renderToStaticMarkup(
      <MarkdownContent content={"> Важно\n\n| Поле | Значение |\n| --- | --- |\n| A | B |\n\n- [x] Готово"} />,
    );
    expect(html).toContain("<blockquote>");
    expect(html).toContain("<table>");
    expect(html).toContain('type="checkbox"');
  });
});
