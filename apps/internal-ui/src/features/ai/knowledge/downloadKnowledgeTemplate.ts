// Каркас YAML-файла для импорта знаний (формат parseKnowledgeYaml):
// documents: [{ title, description?, content }]. description необязателен —
// шаблон показывает оба варианта.
const KNOWLEDGE_TEMPLATE = `documents:
  - title: "Название знания"
    description: "Короткое описание (необязательно)"
    content: |
      Основной текст знания.

  - title: "Название знания без описания"
    content: |
      Основной текст знания.
`;

export function downloadKnowledgeTemplate(): void {
  const url = URL.createObjectURL(
    new Blob([`\uFEFF${KNOWLEDGE_TEMPLATE}`], { type: "text/yaml;charset=utf-8" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = "knowledge-template.yml";
  link.click();
  URL.revokeObjectURL(url);
}
