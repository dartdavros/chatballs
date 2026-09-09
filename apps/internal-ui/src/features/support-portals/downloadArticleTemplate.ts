import { t } from "../../i18n";

// Каркас YAML-файла для импорта статей портала (формат parseArticleYaml):
// articles: [{ slug, categoryPath: [..], locale?, title, summary?, content }].
// summary необязателен — шаблон показывает оба варианта.
//
// Ключи YAML и slug не переводятся: первое читает парсер, второе — часть
// публичного адреса статьи. Переводится то, что человек заменит своим:
// названия разделов, заголовки и текст. Собирается функцией, а не константой:
// константа посчиталась бы при импорте модуля, до выбора языка.
function articleTemplate(): string {
  return `articles:
  - slug: "kak-oformit-vozvrat"
    categoryPath:
      - "${t("portals.template_section_returns")}"
      - "${t("common.appearance")}"
    title: "${t("portals.template_title_return")}"
    summary: "${t("ai.template_description")}"
    content: |
      ${t("portals.template_content")}

  - slug: "garantiya"
    categoryPath:
      - "${t("portals.template_section_returns")}"
    title: "${t("portals.template_title_warranty")}"
    content: |
      ${t("portals.template_content_no_summary")}
`;
}

export function downloadArticleTemplate(): void {
  const url = URL.createObjectURL(
    new Blob([`\uFEFF${articleTemplate()}`], { type: "text/yaml;charset=utf-8" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = "portal-articles-template.yml";
  link.click();
  URL.revokeObjectURL(url);
}
