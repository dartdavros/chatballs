import { fmt, t } from "../../i18n";
import { Icon } from "../../shared/icons";
import type { ApiMessage } from "./apiTypes";
import { useEmailContinuation } from "./EmailContinuationContext";
import { EmailMessageBody } from "./EmailMessageBody";
import { EmailMessageStatus } from "./EmailMessageStatus";
import { FileMessage } from "./FileMessage";
import { et } from "../settings/external-agent/copy";

export function EmailConversationMessage({ message, actor }: { message: ApiMessage; actor?: string }) {
  const mail = useEmailContinuation();
  const operation = mail?.operations.find((row) => row.messageId === message.id);
  const transport = message.transport!;
  const outbound = transport.direction === "OUTBOUND";
  const sender = transport.senderAddress ?? operation?.senderAddress;
  const recipient = transport.recipientAddress ?? operation?.recipient;
  const heading = outbound ? sender ? t("mail.outbound", { recipient: recipient ?? "", sender }) : t("mail.audience", { address: recipient ?? "" })
    : t("mail.inbound", { sender: sender ?? "" });
  return <div className={`sales-message is-email ${outbound ? "operator" : "client"}`}>
    {outbound && <div className="sales-message-avatar">{message.authorAvatarUrl ? <img src={message.authorAvatarUrl} alt="" /> : <span>{message.authorName?.split(/\s+/).slice(0, 2).map((name) => name[0]).join("")}</span>}</div>}
    <div className="email-message-content">
      {actor && <strong className="email-message-actor">{actor}</strong>}
      <div className={`email-message-card ${outbound ? "" : "is-inbound"}`}>
        <header><Icon name="mail" size={13} /><span title={heading}>{heading}</span></header>
        <div className="email-message-body"><strong>{transport.subject ?? operation?.subject}</strong>
          {message.kind === "file" ? <FileMessage message={message} /> : outbound ? <p>{message.text}</p> : <EmailMessageBody html={message.contentHtml} text={message.text} />}
        </div>
        {outbound && message.externalDelivery ? <small>{et(message.externalDelivery.state === "transport_accepted" ? "chat.sentToChannel" : "chat.notConfirmed")}</small>
          : outbound && operation && <EmailMessageStatus operation={operation} />}
      </div>
      <time dateTime={message.createdAt}>{fmt.time(message.createdAt)}</time>
    </div>
  </div>;
}
