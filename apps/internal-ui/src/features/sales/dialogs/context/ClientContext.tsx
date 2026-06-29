import { channelMeta } from "../data";
import type { ApiConversation } from "../model";
import type { SalesDialog } from "../types";
import { ContactRow } from "./ContactRow";
import { ContextSection } from "./ContextSection";

const LIFECYCLE_LABEL: Record<string, string> = { OPEN: "Открыт", CLOSED: "Закрыт", SPAM: "Спам" };
const CONTROL_LABEL: Record<string, string> = { AI: "AI ведёт", HUMAN: "Оператор ведёт", PAUSED: "Пауза" };

function fmt(value?: string): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function ClientContext({ dialog, detail }: { dialog: SalesDialog | null; detail: ApiConversation | null }) {
  if (!dialog) {
    return <div className="sales-client-context"><p className="sales-context-muted">Выберите диалог</p></div>;
  }
  const channel = channelMeta[dialog.channel];
  const messageCount = detail?.messages?.length ?? 0;
  return (
    <div className="sales-client-context">
      <div className="sales-client-hero"><span style={{ background: dialog.avatarBg }}>{dialog.initials}</span><strong>{dialog.name}</strong></div>

      <ContextSection title="КАНАЛ">
        <ContactRow dot={channel.color} title={channel.label} text={detail?.connection?.name ?? "—"} note={dialog.product} />
      </ContextSection>

      <ContextSection title="ДИАЛОГ">
        <div className="sales-summary-grid">
          <div><span>Статус</span><b>{LIFECYCLE_LABEL[detail?.lifecycle ?? ""] ?? "—"}</b></div>
          <div><span>Режим</span><b>{CONTROL_LABEL[detail?.controlMode ?? ""] ?? "—"}</b></div>
          <div><span>Сообщений</span><b>{messageCount}</b></div>
        </div>
        <p className="sales-context-muted">Начат: {fmt(detail?.createdAt)} · активность: {fmt(detail?.lastActivityAt)}</p>
      </ContextSection>
    </div>
  );
}
