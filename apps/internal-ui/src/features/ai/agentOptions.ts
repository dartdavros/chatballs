import type { AgentLinkOption } from "../../shared/content-library/AgentLinkDialog";
import type { AiAgent } from "./model";

/** Агенты для массового прикрепления материалов (библиотека знаний общая,
 * ADR-HUB-0041 §8 — фильтров по отделам больше нет). */
export function agentLinkOptions(agents: AiAgent[]): AgentLinkOption[] {
  return agents.map((agent) => ({
    id: agent.id,
    name: agent.name,
    channelName: agent.channel.name,
    groupName: agent.channel.group?.name ?? null,
  }));
}
