import type { ApiConversation } from "../../../conversations/model";
import { providerKey, providerLabel, providerMeta } from "../../../../shared/providers";
import { t, tn } from "../../../../i18n";
import { shortDate } from "../../../../shared/utils";

// Вкладка «История» (дизайн-базлайн v2, кадр F): диалоги контакта карточками,
// текущий выделен акцентом; в каждой — канал-плашка, агент · статус, превью.

const LIFECYCLE: Record<string, string> = { OPEN: t("sales.open_2"), CLOSED: t("sales.closed_2"), SPAM: t("sales.spam") };

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
        <h4>{t("sales.contact_conversations")}</h4>
        <span>{tn("plural.conversations", total)}</span>
      </div>
      {detail && (
        <div className="history-card is-current">
          <div className="history-card-title"><strong>{t("sales.current_conversation")}</strong><span className="is-open">{LIFECYCLE[detail.lifecycle] ?? detail.lifecycle}</span></div>
          <div className="history-card-meta">
            <ChannelPill provider={detail.connection?.provider ?? null} />
            <span>{detail.channel.name} · {detail.group ? detail.group.name : t("sales.no_group")}</span>
          </div>
          {detail.lastMessage?.text && <p>{detail.lastMessage.text.replace(/\s+/g, " ").slice(0, 120)}</p>}
        </div>
      )}
      {history.length === 0 && <p className="sales-context-muted">{t("sales.there_no_other_conversations_with")}</p>}
      {history.map((item, index) => (
        <div className="history-card" key={item.id}>
          {/* Кадр F: тема — первая реплика клиента, последнее — «Первое обращение»; мета: агент · статус · кто вёл. */}
          <div className="history-card-title"><strong>{index === history.length - 1 ? t("sales.first_enquiry") : (item.topic || item.channelName)}</strong><span>{shortDate(item.lastActivityAt)}</span></div>
          <div className="history-card-meta">
            <ChannelPill provider={item.provider} />
            <span>{item.channelName} · {LIFECYCLE[item.lifecycle] ?? item.lifecycle} · {item.handledBy ? `${t(handledVerbKey(item.handledBy), { name: item.handledBy })}` : "AI"}{item.provider && !providerKey(item.provider) ? ` · ${providerLabel(item.provider)}` : ""}</span>
          </div>
          {item.preview && <p>{item.preview}</p>}
        </div>
      ))}
    </div>
  );
}

// «вела Анна Ким» / «вёл Игорь Савельев» — по окончанию имени (женские имена
// на -а/-я). Правило остаётся русским: в английском обе формы дают одно и то
// же «handled by», и убирать согласование ради этого значило бы испортить
// русский интерфейс ради языка, которому оно безразлично.
function handledVerbKey(name: string): "sales.handled_by_f" | "sales.handled_by_m" {
  const first = name.trim().split(/\s+/)[0] ?? "";
  return /[ая]$/i.test(first) && !/^(Никита|Илья|Кузьма|Савва|Лука|Фома)$/i.test(first)
    ? "sales.handled_by_f"
    : "sales.handled_by_m";
}
