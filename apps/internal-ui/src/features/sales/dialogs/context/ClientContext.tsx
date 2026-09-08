import { useEffect, useState } from "react";

import { Icon } from "../../../../shared/icons";
import { CopyButton } from "../../../../shared/ui-controls";
import { providerMeta } from "../../../../shared/providers";
import { ContactAvatar } from "../../../conversations/ContactAvatar";
import { ContactEditForm } from "../../../conversations/ContactEditForm";
import { DialogControls } from "../../../conversations/DialogControls";
import { requestContact, updateContactCard, type ApiConversation } from "../../../conversations/model";
import type { ConversationListItem } from "../../../conversations/types";
import type { EmployeeGroupRef } from "../../../../types";

// Карточка контакта (дизайн-базлайн v2, решение 5): аватар 64 · канал · имя ·
// описание · поля с иконками и «копировать» · «Позвонить» / «Видеозвонок» под
// полями. Ниже — блок «Диалог» и «Заметка» (DialogControls).

export function ClientContext({
  dialog,
  detail,
  groups = [],
  employees = [],
  applyConversation,
  startCall,
  viewerId = null,
}: {
  dialog: ConversationListItem | null;
  detail: ApiConversation | null;
  groups?: Array<EmployeeGroupRef & { color?: string }>;
  employees?: Array<{ id: number; name: string; avatarUrl?: string | null }>;
  applyConversation?: (updated: ApiConversation) => void;
  startCall?: ((kind: "AUDIO" | "VIDEO") => void) | null;
  viewerId?: number | null;
}) {
  const [requesting, setRequesting] = useState(false);
  const [justRequested, setJustRequested] = useState(false);
  const [requestError, setRequestError] = useState(false);
  const [editing, setEditing] = useState(false);

  // Локальное состояние кнопки принадлежит конкретному диалогу — при переключении сбрасываем.
  useEffect(() => {
    setRequesting(false);
    setJustRequested(false);
    setRequestError(false);
    setEditing(false);
  }, [detail?.id]);

  if (!dialog) {
    return <div className="sales-client-context"><p className="sales-context-muted">Выберите диалог</p></div>;
  }
  const channel = providerMeta[dialog.channel];
  const contact = detail?.contact ?? null;
  const email = contact?.email ?? "";
  const phone = contact?.phone ?? "";
  const username = contact?.username ?? "";
  // Факт запроса контакта считает сервер: сообщение могло уйти вне окна истории,
  // загруженного лентой.
  const alreadyRequested = justRequested || Boolean(detail?.contactRequested);
  const canRequest = Boolean(detail && contact && detail.connection && !phone && detail.lifecycle === "OPEN");
  const isGuest = dialog.channel === "WEB" && !username && !email;

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

  const fields: Array<{ key: string; icon: Parameters<typeof Icon>[0]["name"]; text: string; copy?: string; muted?: boolean }> = [];
  if (phone) fields.push({ key: "phone", icon: "phone", text: phone, copy: phone });
  if (dialog.channel === "EMAIL" && email) fields.push({ key: "email", icon: "mail", text: email, copy: email });
  if (username) fields.push({ key: "username", icon: "send", text: `@${username} · ${channel.label}`, copy: `@${username}` });
  if (isGuest) fields.push({ key: "guest", icon: "message", text: `${channel.label} · ${detail?.connection?.name ?? "виджет"}, анонимная сессия`, muted: true });
  if (fields.length === 0 && detail?.connection) fields.push({ key: "connection", icon: "plug", text: `${channel.label} · ${detail.connection.name}`, muted: true });
  // Компания и город — из карточки контакта (решение 5), без «копировать».
  if (contact?.company) fields.push({ key: "company", icon: "building", text: contact.company });
  if (contact?.city) fields.push({ key: "city", icon: "pin", text: `${contact.city}, Россия` });
  const canEdit = Boolean(detail && contact && applyConversation);

  return (
    <div className="sales-client-context">
      <div className="ctx-contact">
        <div className="ctx-contact-hero">
          <ContactAvatar avatarUrl={dialog.avatarUrl} initials={dialog.initials} background={dialog.avatarBg} className="ctx-contact-avatar" />
          <span className="ctx-channel-pill" style={{ color: channel.color, background: `color-mix(in srgb, ${channel.color} 14%, var(--surface-card))` }}><i style={{ background: channel.color }} />{channel.label}</span>
        </div>
        {editing && detail && contact && applyConversation ? (
          <ContactEditForm
            initial={{ name: contact.name, description: contact.description ?? "", phone: contact.phone ?? "", company: contact.company ?? "", city: contact.city ?? "" }}
            onSubmit={async (fields) => { applyConversation(await updateContactCard(detail.id, fields)); setEditing(false); }}
            onCancel={() => setEditing(false)}
          />
        ) : (
          <>
            <div className="ctx-contact-name">
              <strong>{dialog.name}</strong>
              {canEdit && <button className="ctx-edit-contact" type="button" title="Редактировать контакт" aria-label="Редактировать контакт" onClick={() => setEditing(true)}><Icon name="edit" size={14} /></button>}
            </div>
            <p className={`ctx-contact-description ${contact?.description ? "" : "is-empty"}`}>{contact?.description || "Описания нет"}</p>
          </>
        )}
        <div className="ctx-contact-fields">
          {fields.map((field) => (
            <div className={`ctx-contact-field ${field.muted ? "is-muted" : ""}`} key={field.key}>
              <span><Icon name={field.icon} size={15} /></span>
              <span>{field.text}</span>
              {field.copy && <CopyButton value={field.copy} />}
            </div>
          ))}
        </div>
        {startCall && (
          <div className="ctx-call-buttons">
            {detail?.connection?.audioCalls && <button type="button" onClick={() => startCall("AUDIO")}><Icon name="phone" size={15} />Позвонить</button>}
            {detail?.connection?.videoCalls && <button type="button" onClick={() => startCall("VIDEO")}><Icon name="video" size={15} />Видеозвонок</button>}
          </div>
        )}
        {contact && !phone && (
          <>
            <button className="ctx-request-contact" type="button" onClick={() => void onRequestContact()} disabled={!canRequest || requesting || alreadyRequested}>
              {requesting ? "Отправка…" : alreadyRequested ? "Контакт запрошен" : "Запросить контакт"}
            </button>
            {requestError && <p className="ctx-error">Не удалось отправить запрос — попробуйте ещё раз</p>}
          </>
        )}
      </div>

      {detail && applyConversation && (
        <DialogControls detail={detail} groups={groups} employees={employees} applyConversation={applyConversation} viewerId={viewerId} />
      )}
    </div>
  );
}

// Правка карточки контакта (карандаш у имени): имя, описание, телефон, компания, город.
