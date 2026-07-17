import type { AiAgent } from "../model";

export type ChannelOption = { id: number; code: string; name: string; product: { code: string; name: string } | null };

export type CreateAgentResponse = {
  agent?: AiAgent;
};

export const startPersona = "Ты — AI-ассистент канала обработки. Представляй компанию и помогай клиенту разобраться в продукте.";
export const startTone = "Отвечай дружелюбно и по делу, на русском, простым текстом без markdown-разметки, короткими абзацами.";
export const startInstructions = "Квалифицируй потребность клиента и помогай довести до результата. Не обещай возможности вне базы знаний. При запросе человека или нестандартной ситуации — передавай диалог оператору.";

export function channelDescription(channel: ChannelOption): string {
  return channel.product ? `Без агента · продукт ${channel.product.name}` : "Без агента · без продукта";
}

export function channelMark(channel: ChannelOption): string {
  return (channel.name[0] || channel.code[0] || "").toUpperCase();
}
