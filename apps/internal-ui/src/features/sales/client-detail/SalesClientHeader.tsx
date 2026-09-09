import { Dropdown } from "antd";
import { useState } from "react";

import { ChannelGlyph } from "../../../shared/badges";
import { Icon } from "../../../shared/icons";
import { Button, CopyButton } from "../../../shared/ui-controls";
import { ContactAvatar } from "../../conversations/ContactAvatar";
import { ContactEditForm, type ContactCardFields } from "../../conversations/ContactEditForm";
import type { ClientDetailVm } from "./model";
import { t } from "../../../i18n";

// Шапка карточки контакта (кадр K3): аватар 64 · имя · CID · карандаш ·
// описание · телефон/email/компания/город с «копировать» · бейджи каналов ·
// primary «Открыть диалог» и ⋯. Поля те же, что в контекст-панели чата.

export function SalesClientHeader({ client, canEdit = false, openConversation, onSave }: { client: ClientDetailVm; canEdit?: boolean; openConversation: (conversationId: number) => void; onSave?: (fields: ContactCardFields) => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const targetDialog = client.dialogs.find((dialog) => dialog.active) ?? client.dialogs[0];
  const meta = [
    client.phone ? { icon: "phone" as const, value: client.phone } : null,
    client.email ? { icon: "mail" as const, value: client.email } : null,
    client.company ? { icon: "building" as const, value: client.company } : null,
    client.city ? { icon: "pin" as const, value: client.city } : null,
  ].filter(Boolean) as Array<{ icon: "phone" | "mail" | "building" | "pin"; value: string }>;

  const menuItems = [
    { key: "copy-cid", label: <button type="button" onClick={() => { setMenuOpen(false); void navigator.clipboard?.writeText(client.cid); }}><Icon name="copy" size={15} />{t("sales.copy_cid")}</button> },
  ];

  return (
    <div className="sales-client-card">
      <ContactAvatar avatarUrl={client.avatarUrl || undefined} initials={client.initials} background={client.avatarBg} className="sales-client-detail-avatar" />
      <div className="sales-client-detail-title">
        <div className="sales-client-detail-name-row">
          <h2>{client.name}</h2>
          <code>{client.cid}</code>
          {canEdit && onSave && !editing && <button className="sales-client-edit" type="button" title={t("common.edit_item")} aria-label={t("sales.edit_contact")} onClick={() => setEditing(true)}><Icon name="edit" size={14} /></button>}
        </div>
        {editing && onSave ? (
          <ContactEditForm
            layout="card"
            initial={{ name: client.name, description: client.description, phone: client.rawPhone, company: client.company, city: client.city }}
            onSubmit={async (fields) => { await onSave(fields); setEditing(false); }}
            onCancel={() => setEditing(false)}
          />
        ) : (
          <>
            {client.description && <p>{client.description}</p>}
            <div className="sales-client-detail-meta">
              {meta.map((item) => (
                <span key={item.icon}>
                  <Icon name={item.icon} size={14} strokeWidth={1.9} />
                  {item.value}
                  <CopyButton className="sales-client-copy" value={item.value} />
                </span>
              ))}
              <span className="sales-client-detail-channels">
                {client.channels.map((channel) => (
                  <i style={{ background: channel.bg, color: channel.color }} title={channel.full} key={channel.code}>
                    <ChannelGlyph provider={channel.code} size={13} />{channel.full}
                  </i>
                ))}
              </span>
            </div>
          </>
        )}
      </div>
      {!editing && (
        <div className="sales-client-detail-actions">
          <Button icon="message" variant="primary" disabled={!targetDialog} onClick={() => targetDialog && openConversation(targetDialog.id)}>{t("sales.open_conversation")}</Button>
          <Dropdown menu={{ items: menuItems }} open={menuOpen} onOpenChange={setMenuOpen} trigger={["click"]} overlayClassName="app-dropdown is-wide">
            <button className="sales-client-more" type="button" aria-label={t("sales.contact_actions")}><Icon name="more" size={17} /></button>
          </Dropdown>
        </div>
      )}
    </div>
  );
}
