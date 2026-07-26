import { Icon } from "../../../shared/icons";
import { Button } from "../../../shared/ui-controls";
import type { ClientDetailVm } from "./model";

export function SalesClientHeader({ client, openConversation }: { client: ClientDetailVm; openConversation: (conversationId: number) => void }) {
  const targetDialog = client.dialogs.find((dialog) => dialog.active) ?? client.dialogs[0];

  return (
    <div className="sales-client-detail-header-card">
      <div className="sales-client-detail-header">
        <div className="sales-client-detail-avatar" style={{ background: client.avatarBg }}>{client.initials}</div>
        <div className="sales-client-detail-title">
          <div className="sales-client-detail-name-row">
            <h1>{client.name}</h1>
            <span className="sales-client-cid">{client.cid}</span>
          </div>
          <div className="sales-client-detail-meta">
            <span><Icon name="mail" size={14} /><b>{client.email}</b></span>
            <span><Icon name="phone" size={14} /><b className="muted">{client.phone}</b></span>
            <span className="sales-client-detail-channels">
              {client.channels.map((channel) => (
                <i style={{ background: channel.bg }} key={channel.label}><em style={{ background: channel.color }} /><b style={{ color: channel.color }}>{channel.label}</b></i>
              ))}
            </span>
          </div>
        </div>
        <div className="sales-client-detail-actions">
          <Button className="sales-client-primary" icon="message" variant="primary" disabled={!targetDialog} onClick={() => targetDialog && openConversation(targetDialog.id)}>Открыть диалог</Button>
        </div>
      </div>
    </div>
  );
}
