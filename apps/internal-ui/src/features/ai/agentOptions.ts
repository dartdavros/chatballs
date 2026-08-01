import type { AgentLinkOption } from "../../shared/content-library/AgentLinkDialog";
import type { AiAgent } from "./model";

/**
 * Агенты для массового прикрепления материалов. `departmentCode` сужает список
 * до агентов одного отдела: статьи портала поддержки доступны только агентам
 * поддержки, поэтому предлагать остальных бессмысленно.
 */
export function agentLinkOptions(agents: AiAgent[], departmentCode?: string): AgentLinkOption[] {
  return agents
    .filter((agent) => departmentCode === undefined || agent.channel.department?.code === departmentCode)
    .map((agent) => ({
      id: agent.id,
      name: agent.name,
      channelName: agent.channel.name,
      departmentName: agent.channel.department?.name ?? null,
    }));
}
