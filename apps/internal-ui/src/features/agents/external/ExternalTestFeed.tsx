import { useEffect, useRef } from "react";
import { PreparedMessage } from "@chatballs/ui";
import { resolveApiUrl } from "../../../api/client";
import { t } from "../../../i18n";
import { LogoSpinner } from "../../../shared/icons";
import { HelpTrigger } from "../../settings/external-agent/HelpTrigger";
import { et } from "../../settings/external-agent/copy";
import type { ExternalTestSession } from "./test-model";

export function ExternalTestFeed({ session, failed, agentName, base }: {
  session?: ExternalTestSession; failed: boolean; agentName: string; base: string;
}) {
  const feed = useRef<HTMLDivElement>(null);
  const waiting = session?.state === "waiting" || session?.state === "longWaiting";
  useEffect(() => { if (feed.current) feed.current.scrollTop = feed.current.scrollHeight; }, [session?.messages.length, session?.state, failed]);
  const notice = session?.state === "unknown" ? ["chat.unknownTitle", "chat.unknownHelp"] as const
    : session?.state === "partial" ? ["chat.partialTitle", "chat.partialHelp"] as const
      : session?.state === "blocked" ? ["agent.disabled", "agent.interruptedHelp"] as const
        : session?.state === "handoff" ? ["chat.handoffEvent", "chat.queueHelp"] as const : null;
  return <div className="agent-test-feed" role="log" aria-live="polite" ref={feed}>
    {session?.messages.map(message => message.role === "user" ? <div className="agent-test-client" key={message.id}><div>{message.text}</div></div>
      : <div className="agent-test-reply" key={message.id}><strong>{t("agent_test.agent_name", { name: agentName })}</strong><div>
        {message.formatVersion ? <PreparedMessage content={message} title={t("snapshots.message")} /> : message.text}
        {message.fileUrl && <a className="link" href={resolveApiUrl(`${base}${session.id}/${message.fileUrl}`)}>{message.filename}</a>}
      </div></div>)}
    {waiting && <div className="service-oauth-waiting" data-external-waiting role="status"><span aria-hidden="true"><LogoSpinner size={18} /></span>
      <div><span className="external-help-title"><strong>{et(session.state === "longWaiting" ? "agent.longWait" : "chat.waiting")}</strong><HelpTrigger topic="processing" /></span>
        <span>{et(session.state === "longWaiting" ? "agent.longHelp" : "chat.waitingHelp")}</span></div></div>}
    {notice && <div className="service-oauth-waiting" role="status"><div><strong>{et(notice[0])}</strong><span>{et(notice[1])}</span></div></div>}
    {(failed || session?.state === "error") && <div className="agent-test-error" role="alert">{et("agent.error")}</div>}
  </div>;
}
