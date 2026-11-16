import type { ReactNode } from "react";

import { Icon } from "../../shared/icons";

// Сообщения (решение 4a): у клиента аватара нет — он в шапке; исходящие справа
// с аватаром AI/сотрудника, подписью и отметкой доставки. Внутренний
// комментарий стоит там же, где реплики сотрудников, но клиенту не уходит:
// замок в подписи вместо отметки доставки.
export function MessageBubble({ side, internal = false, confirmed = true, actor, actorColor, authorInitials, authorAvatarUrl, time, children, formatted, footer, note }: { side: "ai" | "client" | "operator"; internal?: boolean; confirmed?: boolean; actor?: string; actorColor?: string; authorInitials?: string; authorAvatarUrl?: string | null; time: string; children: ReactNode; formatted?: boolean; footer?: ReactNode; note?: ReactNode }) {
  return (
    <div className={`sales-message ${side}${internal ? " is-internal" : ""}`}>
      {side !== "client" && (
        <div className="sales-message-avatar" style={side === "ai" && actorColor ? { color: actorColor, background: `color-mix(in srgb, ${actorColor} 14%, var(--surface-card))`, borderColor: `color-mix(in srgb, ${actorColor} 30%, var(--surface-card))` } : undefined}>
          {side === "ai" ? <Icon name="robot" size={16} /> : authorAvatarUrl ? <img src={authorAvatarUrl} alt="" /> : <span>{authorInitials}</span>}
        </div>
      )}
      <div className={`sales-message-content${formatted ? " has-snapshot" : ""}`}>
        {actor && <strong style={actorColor ? { color: actorColor } : undefined}>{internal && <Icon name="lock" size={11} strokeWidth={2.2} />}{actor}</strong>}
        <div>{children}</div>
        <small>{footer}{time}{side !== "client" && !internal && confirmed && <Icon name="check" size={13} />}</small>
        {note}
      </div>
    </div>
  );
}

export function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase();
}
