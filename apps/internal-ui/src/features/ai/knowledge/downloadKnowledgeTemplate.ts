import { t } from "../../../i18n";

// Каркас YAML-файла для импорта знаний (формат parseKnowledgeYaml):
// documents: [{ title, description?, content }]. description необязателен —
// шаблон показывает оба варианта.
//
// Ключи YAML — часть формата и не переводятся: их читает парсер. Переводится
// только то, что человек увидит и заменит своим, — примеры заголовков и текста.
// Шаблон собирается функцией, а не константой: константа посчиталась бы при
// импорте модуля, ещё до того, как стал известен язык.
function knowledgeTemplate(): string {
  return `documents:
  - title: "${t("ai.template_title")}"
    description: "${t("ai.template_description")}"
    content: |
      ${t("ai.template_content")}

  - title: "${t("ai.template_title_no_description")}"
    content: |
      ${t("ai.template_content")}
`;
}

export function downloadKnowledgeTemplate(): void {
  const url = URL.createObjectURL(
    new Blob([`\uFEFF${knowledgeTemplate()}`], { type: "text/yaml;charset=utf-8" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = "knowledge-template.yml";
  link.click();
  URL.revokeObjectURL(url);
}
