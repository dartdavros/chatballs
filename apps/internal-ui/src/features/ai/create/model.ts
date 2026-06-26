import type { Product } from "../../../types";
import type { AiAgent, AiRelease } from "../model";

export type KnowledgeDocument = {
  id: number;
  title: string;
  category: string;
  versions: Array<{ version: number; status: string }>;
};

export type CreateAgentResponse = {
  agent?: AiAgent;
  release?: AiRelease;
};

export const modelOptions = [
  { value: "gpt-4o-mini", label: "gpt-4o-mini · по умолчанию" },
  { value: "gpt-4o", label: "gpt-4o · точнее, дороже" },
  { value: "claude-3.5-sonnet", label: "claude-3.5-sonnet" },
  { value: "claude-3.5-haiku", label: "claude-3.5-haiku" },
];

export const startSystemPrompt = "Ты — sales-агент продукта. Отвечай дружелюбно и по делу, на русском. Квалифицируй потребность клиента, предлагай подходящее предложение и оформляй покупку. Не обещай возможности вне базы знаний. При запросе человека или нестандартной ситуации — передавай диалог оператору.";

export function productDescription(product: Product): string {
  return `Без sales-агента · ${product.offers.length} предложения`;
}

export function productMark(product: Product): string {
  return (product.name[0] || product.code[0] || "").toUpperCase();
}

export function knowledgeMeta(document: KnowledgeDocument): string {
  const version = document.versions[0]?.version ?? 1;
  return `${document.category} · v${version}`;
}
