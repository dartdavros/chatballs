import type { ApiConversation } from "../../../conversations/model";
import { providerKey, providerLabel, providerMeta } from "../../../../shared/providers";

// Вкладка «История» (дизайн-базлайн v2, кадр F): диалоги контакта карточками,
// текущий выделен акцентом; в каждой — канал-плашка, агент · статус, превью.

const LIFECYCLE: Record<string, string> = { OPEN: "открыт", CLOSED: "закрыт", SPAM: "спам" };

function fmtDate(value: string): string {
  return new Date(value).toLocaleDateString("ru-RU", { day: "numeric", month: "short" }).replace(".", "");
}

function pluralDialogs(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return `${count} диалог`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return `${count} диалога`;
  return `${count} диалогов`;
}

function ChannelPill({ provider }: { provider: string | null }) {
  const key = provider ? providerKey(provider) : null;
  if (!key) return null;
  const meta = providerMeta[key];
  return (
    <b className="history-channel" style={{ color: meta.color, background: `color-mix(in srgb, ${meta.color} 14%, var(--surface-card))` }}>
      <i style={{ background: meta.color }} />{meta.label}
    </b>
  );
}

export function HistoryContext({ detail }: { detail: ApiConversation | null }) {
  const history = detail?.history ?? [];
  const total = (detail ? 1 : 0) + history.length;
  return (
    <div className="sales-history-context">
      <div className="history-head">
        <h4>Диалоги контакта</h4>
        <span>{pluralDialogs(total)}</span>
      </div>
      {detail && (
        <div className="history-card is-current">
          <div className="history-card-title"><strong>Текущий диалог</strong><span className="is-open">{LIFECYCLE[detail.lifecycle] ?? detail.lifecycle}</span></div>
          <div className="history-card-meta">
            <ChannelPill provider={detail.connection?.provider ?? null} />
            <span>{detail.channel.name}{detail.group ? ` · ${detail.group.name}` : ""}</span>
          </div>
          {detail.lastMessage?.text && <p>{detail.lastMessage.text.replace(/\s+/g, " ").slice(0, 120)}</p>}
        </div>
      )}
      {history.length === 0 && <p className="sales-context-muted">Других диалогов с этим контактом нет</p>}
      {history.map((item, index) => (
        <div className="history-card" key={item.id}>
          <div className="history-card-title"><strong>{index === history.length - 1 ? "Первое обращение" : item.channelName}</strong><span>{fmtDate(item.lastActivityAt)}</span></div>
          <div className="history-card-meta">
            <ChannelPill provider={item.provider} />
            <span>{item.channelName} · {LIFECYCLE[item.lifecycle] ?? item.lifecycle}{item.provider && !providerKey(item.provider) ? ` · ${providerLabel(item.provider)}` : ""}</span>
          </div>
          {item.preview && <p>{item.preview}</p>}
        </div>
      ))}
    </div>
  );
}
