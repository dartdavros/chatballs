import { useState, type ComponentProps } from "react";
import { PreparedMessage, snapshotDocument, snapshotText } from "@chatballs/ui";
import { fmt, t } from "../../i18n";
import { Icon } from "../../shared/icons";
import type { ApiMessage } from "./apiTypes";
import { MessageBubble } from "./MessageBubble";
import "./snapshot-message.css";

export function SnapshotMessage({ message, bubble }: { message: ApiMessage; bubble: Omit<ComponentProps<typeof MessageBubble>, "children"> }) {
  const [expanded, setExpanded] = useState(false);
  const html = Boolean(snapshotDocument(message));
  const footer = html && message.template?.name && <span className="conversation-snapshot-meta">
      <span><Icon name="layout" size={11} />{message.template.name}</span>
      <button type="button" className="link is-muted" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>
        {t(expanded ? "snapshots.hide_text" : "snapshots.show_text")}
      </button>
    </span>;
  const note = html && message.template?.name && message.templateUpdatedAt && <aside className="conversation-snapshot-update">
      <Icon name="info" size={13} />
      {t("snapshots.updated", { name: message.template.name, date: fmt.shortDate(message.templateUpdatedAt) })}
    </aside>;
  return <MessageBubble {...bubble} formatted={html} footer={<>{bubble.footer}{footer}</>} note={note}>
    <PreparedMessage content={message} title={t("snapshots.message")} />
    {html && expanded && <div className="conversation-snapshot-text">{snapshotText(message.text)}</div>}
  </MessageBubble>;
}
