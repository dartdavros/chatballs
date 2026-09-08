import type { AgentLinkOption } from "../../shared/content-library/AgentLinkDialog";
import type { AgentRef } from "../agents/model";

/** Агенты для массового прикрепления материалов (библиотека знаний общая,
 * ADR-CHATBALLS-0041 §8). Bulk-эндпоинты знаний адресуют AIAgent, поэтому id —
 * aiAgentId карточки. */
export function agentLinkOptions(agents: AgentRef[]): AgentLinkOption[] {
  // У канала без AI-агента прикреплять материалы не к чему.
  return agents
    .filter((agent): agent is AgentRef & { aiAgentId: number } => agent.aiAgentId !== null)
    .map((agent) => ({
      id: agent.aiAgentId,
      name: agent.name,
      groupName: agent.groupName,
    }));
}
