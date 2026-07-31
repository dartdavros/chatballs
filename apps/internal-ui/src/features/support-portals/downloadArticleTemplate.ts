// Каркас YAML-файла для импорта статей портала (формат parseArticleYaml):
// articles: [{ slug, categoryPath: [..], locale?, title, summary?, content }].
// summary необязателен — шаблон показывает оба варианта.
const ARTICLE_TEMPLATE = `articles:
  - slug: "kak-oformit-vozvrat"
    categoryPath:
      - "Возврат"
      - "Оформление"
    title: "Как оформить возврат"
    summary: "Короткое описание (необязательно)"
    content: |
      Текст статьи в Markdown.

  - slug: "garantiya"
    categoryPath:
      - "Возврат"
    title: "Гарантия"
    content: |
      Текст статьи без описания.
`;

export function downloadArticleTemplate(): void {
  const url = URL.createObjectURL(
    new Blob([`\uFEFF${ARTICLE_TEMPLATE}`], { type: "text/yaml;charset=utf-8" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = "portal-articles-template.yml";
  link.click();
  URL.revokeObjectURL(url);
}
