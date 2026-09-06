import { useState } from "react";

import { Icon } from "../../../shared/icons";
import { Button } from "../../../shared/ui-controls";
import { ContactAvatar } from "../../conversations/ContactAvatar";
import { ContactEditForm, type ContactCardFields } from "../../conversations/ContactEditForm";
import type { ClientDetailVm } from "./model";

// Шапка карточки контакта: те же поля, что в контекст-панели чата (фото,
// описание, компания, город), правка карандашом у имени.
export function SalesClientHeader({ client, canEdit = false, openConversation, onSave }: { client: ClientDetailVm; canEdit?: boolean; openConversation: (conversationId: number) => void; onSave?: (fields: ContactCardFields) => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const targetDialog = client.dialogs.find((dialog) => dialog.active) ?? client.dialogs[0];

  return (
    <div className="sales-client-detail-header-card">
      <div className="sales-client-detail-header">
        <ContactAvatar avatarUrl={client.avatarUrl || undefined} initials={client.initials} background={client.avatarBg} className="sales-client-detail-avatar" />
        <div className="sales-client-detail-title">
          {editing && onSave ? (
            <ContactEditForm
              initial={{ name: client.name, description: client.description, phone: client.rawPhone, company: client.company, city: client.city }}
              onSubmit={async (fields) => { await onSave(fields); setEditing(false); }}
              onCancel={() => setEditing(false)}
            />
          ) : (
          <>
          <div className="sales-client-detail-name-row">
            <h1>{client.name}</h1>
            <span className="sales-client-cid">{client.cid}</span>
            {canEdit && onSave && <button className="ctx-edit-contact" type="button" title="Редактировать контакт" aria-label="Редактировать контакт" onClick={() => setEditing(true)}><Icon name="edit" size={14} /></button>}
          </div>
          {client.description && <p className="sales-client-detail-description">{client.description}</p>}
          <div className="sales-client-detail-meta">
            <span><Icon name="mail" size={14} /><b>{client.email}</b></span>
            <span><Icon name="phone" size={14} /><b className="muted">{client.phone}</b></span>
            {client.company && <span><Icon name="building" size={14} /><b>{client.company}</b></span>}
            {client.city && <span><Icon name="pin" size={14} /><b>{client.city}</b></span>}
            <span className="sales-client-detail-channels">
              {client.channels.map((channel) => (
                <i style={{ background: channel.bg }} key={channel.label}><em style={{ background: channel.color }} /><b style={{ color: channel.color }}>{channel.label}</b></i>
              ))}
            </span>
          </div>
          </>
          )}
        </div>
        <div className="sales-client-detail-actions">
          <Button className="sales-client-primary" icon="message" variant="primary" disabled={!targetDialog} onClick={() => targetDialog && openConversation(targetDialog.id)}>Открыть диалог</Button>
        </div>
      </div>
    </div>
  );
}
