import { useEffect, useState } from "react";

import { Icon } from "../../../../shared/icons";
import { providerMeta } from "../../../../shared/providers";
import { ContactAvatar } from "../../../conversations/ContactAvatar";
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
  // Запрос уже отправлен, если в диалоге есть сообщение kind=contact_request (detail поллится каждые 3 с).
  const alreadyRequested = justRequested || (detail?.messages ?? []).some((m) => m.kind === "contact_request");
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
            conversationId={detail.id}
            initial={{ name: contact.name, description: contact.description ?? "", phone: contact.phone ?? "", company: contact.company ?? "", city: contact.city ?? "" }}
            onSaved={(updated) => { applyConversation(updated); setEditing(false); }}
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

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className={copied ? "is-copied" : ""}
      aria-label="Скопировать"
      title={copied ? "Скопировано" : "Скопировать"}
      onClick={() => {
        void navigator.clipboard?.writeText(value).then(() => {
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1200);
        });
      }}
    >
      <Icon name={copied ? "check" : "copy"} size={13} />
    </button>
  );
}

// Правка карточки контакта (карандаш у имени): имя, описание, телефон, компания, город.
function ContactEditForm({
  conversationId,
  initial,
  onSaved,
  onCancel,
}: {
  conversationId: number;
  initial: { name: string; description: string; phone: string; company: string; city: string };
  onSaved: (updated: ApiConversation) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [errorText, setErrorText] = useState("");
  const set = (key: keyof typeof form) => (event: { target: { value: string } }) => setForm((prev) => ({ ...prev, [key]: event.target.value }));

  async function save() {
    if (!form.name.trim()) {
      setErrorText("Имя не может быть пустым");
      return;
    }
    setSaving(true);
    setErrorText("");
    try {
      onSaved(await updateContactCard(conversationId, form));
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : "Не удалось сохранить");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="ctx-contact-edit" onSubmit={(event) => { event.preventDefault(); void save(); }}>
      <input value={form.name} onChange={set("name")} placeholder="Имя" aria-label="Имя" autoFocus />
      <textarea value={form.description} onChange={set("description")} placeholder="Описание" aria-label="Описание" rows={2} />
      <input value={form.phone} onChange={set("phone")} placeholder="Телефон" aria-label="Телефон" />
      <input value={form.company} onChange={set("company")} placeholder="Компания" aria-label="Компания" />
      <input value={form.city} onChange={set("city")} placeholder="Город" aria-label="Город" />
      {errorText && <p className="ctx-error">{errorText}</p>}
      <div className="ctx-note-actions">
        <button type="button" onClick={onCancel} disabled={saving}>Отмена</button>
        <button type="submit" className="primary" disabled={saving}>Сохранить</button>
      </div>
    </form>
  );
}
