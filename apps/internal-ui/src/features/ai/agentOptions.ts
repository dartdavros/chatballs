import type { AgentLinkOption } from "../../shared/content-library/AgentLinkDialog";
import type { AgentCard } from "../agents/model";

/** Агенты для массового прикрепления материалов (библиотека знаний общая,
 * ADR-HUB-0041 §8). Bulk-эндпоинты знаний адресуют AIAgent, поэтому id —
 * aiAgentId карточки. */
export function agentLinkOptions(agents: AgentCard[]): AgentLinkOption[] {
  return agents.map((agent) => ({
    id: agent.aiAgentId,
    name: agent.name,
    groupName: agent.groupName,
  }));
}
