import { fmt, t } from "../../i18n";
import { Icon } from "../../shared/icons";
import { TransferTimelineEvent } from "../transfers/TransferTimelineEvent";
import { EmailMessageBody } from "./EmailMessageBody";
import { EmailConversationMessage } from "./EmailConversationMessage";
import { FileMessage } from "./FileMessage";
import { MessageBubble, initialsOf } from "./MessageBubble";
import { ConversationText } from "./ConversationText";
import { VoiceMessage } from "./VoiceMessage";
import { SnapshotMessage } from "./SnapshotMessage";
import type { ApiMessage } from "./apiTypes";
import type { ConversationListItem } from "./types";

export function ConversationMessage({ message, dialog, viewerId }: { message: ApiMessage; dialog: ConversationListItem; viewerId: number | null }) {
  if (message.author === "SYSTEM") {
    if (message.transferId) return <TransferTimelineEvent conversationId={Number(dialog.id)} transferId={message.transferId} fallback={message.text} createdAt={message.createdAt} />;
    // Системное событие (кадры B, C): передача — предупреждение, взятие и
    // возврат — акцент. Тон выбирается по коду события, а не по словам в
    // тексте: текст приходит на языке читателя и на английском не совпал бы
    // ни с одной русской регуляркой.
    // «Не взял — вернулся в очередь» окрашено предупреждением намеренно (макет
    // Q4): это не факт из истории, а сорванная договорённость.
    const tone = message.systemEvent === "ai_handed_over"
      || message.systemEvent === "ai_unavailable"
      || message.systemEvent === "assignment_expired"
      ? "warning"
      : message.systemEvent === "operator_took"
        || message.systemEvent === "returned_to_ai"
        || message.systemEvent === "returned_to_queue"
        || message.systemEvent === "assigned_to"
        ? "claimed"
        : "";
    return <div className={`sales-event-chip ${tone}`}><Icon name="clock" size={12} />{message.text}<span>·</span>{fmt.time(message.createdAt)}</div>;
  }
  const side = message.author === "CONTACT" ? "client" : message.author === "OPERATOR" ? "operator" : "ai";
  // Подпись исходящего (решение 4a): «AI · Консультант», «Анна Ким», «Елена Кузнецова · вы».
  const actor = message.author === "AI"
    ? `AI · ${dialog.agentName}`
    : message.author === "OPERATOR"
      ? `${message.authorName || t("common.operator")}${viewerId != null && message.authorUserId === viewerId ? t("common.you_suffix") : ""}`
      : undefined;
  if (message.transport?.provider === "EMAIL") return <EmailConversationMessage message={message} actor={actor} />;
  if (message.author === "AI" && !["voice", "file"].includes(message.kind ?? "")
    && (message.formatVersion !== undefined || message.presentation !== undefined)) {
    return <SnapshotMessage message={message} bubble={{ side, actor, actorColor: dialog.agentColor, time: fmt.time(message.createdAt) }} />;
  }
  return (
    <MessageBubble side={side} actor={actor} actorColor={message.author === "AI" ? dialog.agentColor : undefined} time={fmt.time(message.createdAt)} authorInitials={message.authorName ? initialsOf(message.authorName) : ""} authorAvatarUrl={message.authorAvatarUrl ?? null}>
      {message.kind === "voice"
        ? <VoiceMessage message={message} />
        : message.kind === "file"
          ? <FileMessage message={message} syntax={dialog.channel === "TG" ? "telegram" : "markdown"} />
        : message.author === "CONTACT" && dialog.channel === "EMAIL"
          ? <EmailMessageBody html={message.contentHtml} text={message.text} />
          : <ConversationText text={message.text} syntax={dialog.channel === "TG" ? "telegram" : "markdown"} />}
    </MessageBubble>
  );
}
