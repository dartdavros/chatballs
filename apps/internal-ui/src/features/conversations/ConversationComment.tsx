import { fmt, t } from "../../i18n";
import type { ApiComment } from "./commentApi";
import { MessageBubble, initialsOf } from "./MessageBubble";
import { ConversationText } from "./ConversationText";

/** Внутренний комментарий в общей ленте (кадр K1): видят только сотрудники. */
export function ConversationComment({ comment, viewerId }: { comment: ApiComment; viewerId: number | null }) {
  const author = `${comment.author.name}${viewerId != null && comment.author.id === viewerId ? t("common.you_suffix") : ""}`;
  return (
    <MessageBubble side="operator" internal actor={t("comments.feed_actor", { name: author })} time={fmt.time(comment.createdAt)} authorInitials={initialsOf(comment.author.name)} authorAvatarUrl={comment.author.avatarUrl ?? null}>
      <ConversationText text={comment.text} />
    </MessageBubble>
  );
}
