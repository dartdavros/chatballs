import { useEffect, useState } from "react";

import { providerMeta } from "../../../../shared/providers";
import { FieldRow } from "../../../conversations/FieldRow";
import { ContextSection } from "../../../conversations/ContextSection";
import { requestContact, type ApiConversation } from "../../../conversations/model";
import type { ConversationListItem } from "../../../conversations/types";

const LIFECYCLE_LABEL: Record<string, string> = { OPEN: "Открыт", CLOSED: "Закрыт", SPAM: "Спам" };
const CONTROL_LABEL: Record<string, string> = { AI: "AI ведёт", HUMAN: "Человек", PAUSED: "Пауза" };

function fmt(value?: string): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function ClientContext({ dialog, detail }: { dialog: ConversationListItem | null; detail: ApiConversation | null }) {
  const [requesting, setRequesting] = useState(false);
  const [justRequested, setJustRequested] = useState(false);
  const [requestError, setRequestError] = useState(false);

  // Локальное состояние кнопки принадлежит конкретному диалогу — при переключении сбрасываем.
  useEffect(() => {
    setRequesting(false);
    setJustRequested(false);
    setRequestError(false);
  }, [detail?.id]);

  if (!dialog) {
    return <div className="sales-client-context"><p className="sales-context-muted">Выберите диалог</p></div>;
  }
  const channel = providerMeta[dialog.channel];
  const messageCount = detail?.messages?.length ?? 0;

  const contact = detail?.contact ?? null;
  const email = contact?.email ?? "";
  const phone = contact?.phone ?? "";
  const username = contact?.username ?? "";
  // Запрос уже отправлен, если в диалоге есть сообщение kind=contact_request (detail поллится каждые 3 с).
  const alreadyRequested = justRequested || (detail?.messages ?? []).some((m) => m.kind === "contact_request");
  const canRequest = Boolean(detail && contact && detail.connection && !phone && detail.lifecycle === "OPEN");

  async function onRequestContact() {
    if (!detail || requesting) return;
    setRequesting(true);
    setRequestError(false);
    try {
      await requestContact(detail.id);
      setJustRequested(true);
    } catch {
      setRequestError(true);
    } finally {
      setRequesting(false);
    }
  }

  return (
    <div className="sales-client-context">
      <div className="sales-client-hero"><span style={{ background: dialog.avatarBg }}>{dialog.initials}</span><strong>{dialog.name}</strong></div>

      <ContextSection title="КОНТАКТ">
        {dialog.channel === "EMAIL" ? (
          <FieldRow icon="mail" title={email || "—"} text="Email" mono={Boolean(email)} muted={!email} />
        ) : (
          <FieldRow dot={channel.color} title={username ? `@${username}` : "—"} text={`Логин · ${channel.label}`} />
        )}
        <FieldRow icon="phone" title={phone || "—"} text="Телефон" mono={Boolean(phone)} muted={!phone} />
        {contact && !phone && (
          <>
            <button className="sales-secondary-action" style={{ width: "100%", marginTop: 8 }} onClick={() => void onRequestContact()} disabled={!canRequest || requesting || alreadyRequested}>
              {requesting ? "Отправка…" : alreadyRequested ? "Контакт запрошен" : "Запросить контакт"}
            </button>
            {requestError && <p className="sales-context-muted" style={{ color: "#cf1322" }}>Не удалось отправить запрос — попробуйте ещё раз</p>}
          </>
        )}
      </ContextSection>

      <ContextSection title="КАНАЛ">
        <FieldRow dot={channel.color} title={channel.label} text={detail?.connection?.name ?? "—"} note={dialog.product} />
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
