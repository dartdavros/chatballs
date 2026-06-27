import type { AiAgent, AiRelease } from "../model";

export type ChannelOption = { id: number; code: string; name: string; product: { code: string; name: string } | null };

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
  { value: "anthropic/claude-sonnet-4.6", label: "Sonnet 4.6 · по умолчанию" },
  { value: "openai/gpt-4o-mini", label: "gpt-4o-mini · дешевле" },
];

export const startSystemPrompt = "Ты — агент канала обработки. Отвечай дружелюбно и по делу, на русском. Квалифицируй потребность клиента и помогай довести до результата. Не обещай возможности вне базы знаний. При запросе человека или нестандартной ситуации — передавай диалог оператору.";

export function channelDescription(channel: ChannelOption): string {
  return channel.product ? `Без агента · продукт ${channel.product.name}` : "Без агента · без продукта";
}

export function channelMark(channel: ChannelOption): string {
  return (channel.name[0] || channel.code[0] || "").toUpperCase();
}

export function knowledgeMeta(document: KnowledgeDocument): string {
  const version = document.versions[0]?.version ?? 1;
  return `${document.category} · v${version}`;
}
