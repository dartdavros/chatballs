import { ContextSection } from "../../conversations/ContextSection";
import type { ApiConversation } from "../../conversations/model";

// История прошлых support-обращений по subject_key (ADR-HUB-0002). Backend уже
// отдаёт detail.history, сгруппированную по support_identity_snapshot_id
// (_conversation_history в conversations/serializers.py).
const LIFECYCLE: Record<string, string> = { OPEN: "открыт", CLOSED: "закрыт", SPAM: "спам" };

function fmtDate(value: string): string {
  return new Date(value).toLocaleDateString("ru-RU", { day: "2-digit", month: "short" });
}

export function SupportHistory({ detail }: { detail: ApiConversation | null }) {
  const history = detail?.history ?? [];
  return (
    <div className="sales-history-context">
      <ContextSection title="ПРЕДЫДУЩИЕ ОБРАЩЕНИЯ">
        <div className="sales-history-card current">
          <div><strong>Текущее обращение</strong><span>сейчас</span></div>
          <p>{detail ? `${detail.channel.name} · ${LIFECYCLE[detail.lifecycle] ?? detail.lifecycle}` : "—"}</p>
        </div>
        {history.length === 0 && <p className="sales-context-muted">Других обращений этого клиента нет</p>}
        {history.map((item) => (
          <div className="sales-history-card" key={item.id}>
            <div><strong>{item.channelName}</strong><span>{fmtDate(item.lastActivityAt)}</span></div>
            <p>{(item.provider ?? "—")} · {LIFECYCLE[item.lifecycle] ?? item.lifecycle}{item.preview ? `. ${item.preview}` : ""}</p>
          </div>
        ))}
      </ContextSection>
    </div>
  );
}
