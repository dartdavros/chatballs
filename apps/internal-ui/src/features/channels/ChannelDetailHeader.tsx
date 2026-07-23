import { ProductMark, StatusPill } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import type { Channel } from "./types";

export function ChannelDetailHeader({
  channel,
  canEdit,
  editing,
  busy,
  onEdit,
  onSave,
  onCancel,
}: {
  channel: Channel;
  canEdit: boolean;
  editing: boolean;
  busy: boolean;
  onEdit: () => void;
  onSave: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="channel-detail-header">
      <div>
        <div className="channel-detail-title">
          <StatusPill status={channel.isActive ? "active" : "archived"} />
          <h1>{channel.name}</h1>
        </div>
        <div className="channel-detail-meta">
          <code>{channel.code}</code>
          <span>·</span>
          {channel.departmentName ?? "Без отдела"}
          <span>·</span>
          {channel.product ? <ProductMark product={channel.product} /> : "— непродуктовый"}
        </div>
      </div>
      <div className="channel-detail-actions">
        {canEdit && !editing && (
          <Button variant="secondary" icon="edit" onClick={onEdit}>Изменить</Button>
        )}
        {editing && (
          <>
            <Button variant="secondary" disabled={busy} onClick={onCancel}>Отмена</Button>
            <Button variant="primary" disabled={busy} onClick={onSave}>Сохранить</Button>
          </>
        )}
      </div>
    </div>
  );
}
