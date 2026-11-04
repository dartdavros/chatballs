import { useEffect, useRef } from "react";
import { PreparedMessage } from "@chatballs/ui";
import { t } from "../../../i18n";
import { ToolCallChip } from "../../../shared/tool-calls/ToolCallChip";
import type { TestTurn } from "./model";
import { TestActionCard } from "./TestActionCard";

export function TestChatFeed({ turns, agentName }: { turns: TestTurn[]; agentName: string }) {
  const feed = useRef<HTMLDivElement>(null);
  useEffect(() => { if (feed.current) feed.current.scrollTop = feed.current.scrollHeight; }, [turns]);
  return <div className="agent-test-feed" role="log" aria-live="polite" ref={feed}>
    {turns.map((turn, index) => <div key={index}>
      <div className="agent-test-client"><div>{turn.message}</div></div>
      <ToolCallChip calls={turn.calls} createdAt={turn.createdAt} />
      {turn.serviceActions?.map((action, index) => <TestActionCard key={`${action.runId ?? "preview"}:${index}`} action={action} />)}
      {turn.reply !== undefined && <div className="agent-test-reply">
        <strong>{t("agent_test.agent_name", { name: agentName })}</strong><div>
          {turn.presentation !== undefined || turn.formatVersion !== undefined
            ? <PreparedMessage content={{ ...turn, text: turn.reply }} title={t("snapshots.message")} /> : turn.reply}
        </div>
      </div>}
      {turn.error && <div className="agent-test-error" role="alert">{turn.error}</div>}
    </div>)}
  </div>;
}
