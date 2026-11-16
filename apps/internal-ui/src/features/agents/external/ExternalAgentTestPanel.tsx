import { useEffect, useId, useRef, useState } from "react";
import { t } from "../../../i18n";
import { Icon } from "../../../shared/icons";
import { ErrorScreen, LoadingState } from "../../../shared/ui";
import { et } from "../../settings/external-agent/copy";
import type { AgentCard } from "../model";
import { ExternalTestClientData } from "./ExternalTestClientData";
import { ExternalTestFeed } from "./ExternalTestFeed";
import { useExternalTestChat } from "./useExternalTestChat";
import { validValues } from "./test-model";
import "../test-chat/styles.css";
import "../actions/actions.css";
import "./test.css";

export function ExternalAgentTestPanel({ card, onClose }: { card: AgentCard; onClose: () => void }) {
  const chat = useExternalTestChat(card.id);
  const [message, setMessage] = useState("");
  const titleId = useId(), panel = useRef<HTMLElement>(null), input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    panel.current?.focus();
    return () => opener?.focus();
  }, []);
  const waiting = chat.session?.state === "waiting" || chat.session?.state === "longWaiting";
  const stopped = chat.session && !["idle", "ready"].includes(chat.session.state) && !waiting;
  const disabled = chat.busy || waiting || !!stopped || chat.failed || !chat.definition || !card.externalExecution?.available;
  return <aside className="agent-test-panel" ref={panel} tabIndex={-1} role="dialog" aria-labelledby={titleId}
    onKeyDown={event => { if (event.key === "Escape") { event.stopPropagation(); onClose(); } }}>
    <header className="agent-test-head"><div><strong id={titleId}>{t("agent_test.title")}</strong>
      <small>{et("agent.external")} · {card.externalExecution?.name}</small></div>
      <button type="button" disabled={chat.busy || waiting} title={t("agent_test.restart")} aria-label={t("agent_test.restart")}
        onClick={() => void chat.restart().then(() => { setMessage(""); input.current?.focus(); })}><Icon name="refresh" size={15} strokeWidth={2.2} /></button>
      <button type="button" title={t("common.close")} aria-label={t("common.close")} onClick={onClose}><Icon name="close" size={15} strokeWidth={2.4} /></button>
    </header>
    <div className="agent-action-test-mode is-warning" data-external-test><strong>{et("test.externalMode")}</strong><p>{et("test.externalTestWarning")}</p></div>
    {chat.loadError ? <ErrorScreen retry={chat.reload} /> : !chat.definition ? <LoadingState />
      : <ExternalTestClientData definition={chat.definition} values={chat.values} change={chat.setValues} disabled={chat.busy || !!chat.session} />}
    <ExternalTestFeed session={chat.session} failed={chat.failed} agentName={card.name} base={chat.base} />
    <form className="agent-test-composer" onSubmit={event => {
      event.preventDefault();
      if (!disabled && message.trim() && chat.definition && validValues(chat.definition, chat.values))
        void chat.send(message.trim()).then(sent => { if (sent) setMessage(""); });
    }}><div><input ref={input} value={message} aria-label={t("agent_test.placeholder")} placeholder={t("agent_test.placeholder")}
      onChange={event => setMessage(event.target.value)} disabled={disabled} maxLength={10000} />
      <button type="submit" disabled={disabled || !message.trim() || !chat.definition || !validValues(chat.definition, chat.values)} aria-busy={chat.busy || waiting}>{t("conversations.send")}</button>
    </div></form>
  </aside>;
}
