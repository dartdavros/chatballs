import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { Pagination } from "./Pagination";

// Единственный подвал со страницами: он же в порталах, статьях, контактах,
// сотрудниках, агентах и журнале аудита.

function render(page: number, pageCount: number, note?: string): string {
  return renderToStaticMarkup(
    <Pagination note={note} page={page} pageCount={pageCount} onPage={() => undefined} />,
  );
}

describe("Pagination", () => {
  it("гасит стрелки на границах набора", () => {
    const first = render(1, 3);
    expect(first).toContain('aria-label="Предыдущая страница" class="pager-step" disabled');
    expect(first).not.toContain('aria-label="Следующая страница" class="pager-step" disabled');
    const last = render(3, 3);
    expect(last).toContain('aria-label="Следующая страница" class="pager-step" disabled');
  });

  it("отмечает текущую страницу", () => {
    expect(render(2, 3)).toContain('aria-current="page"');
  });

  it("сворачивает длинный набор многоточиями", () => {
    const markup = render(5, 20);
    expect(markup).toContain("…");
    expect(markup).toContain(">20<");
  });

  it("показывает подпись слева", () => {
    expect(render(1, 2, "Показано 20 из 45")).toContain("Показано 20 из 45");
  });
});
