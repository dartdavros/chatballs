import { fmt } from "../../i18n";
import { Icon, LogoSpinner } from "../../shared/icons";
import { HelpTrigger } from "../settings/external-agent/HelpTrigger";
import { et } from "../settings/external-agent/copy";
import { MessageBubble } from "./MessageBubble";
import { ConversationText } from "./ConversationText";
import type { ExternalNotice } from "./apiTypes";
import "../integrations/services/services.css";
import "../settings/external-agent/styles.css";

export function ExternalExecutionWaiting({ long }: { long: boolean }) {
  return <div className="service-oauth-waiting" role="status" data-external-waiting><span aria-hidden="true"><LogoSpinner size={18} /></span>
    <div><span className="external-help-title"><strong>{et(long ? "chat.longWaiting" : "chat.waiting")}</strong>{long && <HelpTrigger topic="processing" />}</span>
      <span>{et(long ? "chat.longWaitingHelp" : "chat.waitingHelp")}</span></div></div>;
}

const titles = { handoff: "chat.handoffEvent", unavailable: "chat.unavailableEvent", timeout: "chat.timeoutEvent", voiceFailure: "chat.voiceFailure" } as const;
const notes = { handoff: "chat.queueHelp", unavailable: "chat.queueHelp", timeout: "chat.queueHelp", voiceFailure: "chat.voiceFailureHelp",
  suppressed: "chat.suppressed", unknown: "chat.unknownHelp", partial: "chat.partialHelp" } as const;
export function ExternalExecutionNotice({ notice, agentColor }: { notice: ExternalNotice; agentColor: string }) {
  const title = titles[notice.kind as keyof typeof titles];
  const fromAgent = notice.kind === "handoff";
  return <>
    {title && <div className="sales-event-chip warning"><Icon name="clock" size={12} />{et(title)}<span>·</span>{fmt.time(notice.createdAt)}</div>}
    <MessageBubble side={fromAgent ? "ai" : "operator"} internal actor={et(fromAgent ? "chat.externalActor" : "chat.systemActor")}
      actorColor={fromAgent ? agentColor : undefined} authorInitials="CB" time={fmt.time(notice.createdAt)}>
      {(notice.kind === "unknown" || notice.kind === "partial") && <strong>{et(notice.kind === "unknown" ? "chat.unknownTitle" : "chat.partialTitle")}</strong>}
      <ConversationText text={notice.summary || et(notes[notice.kind])} />
    </MessageBubble>
  </>;
}
