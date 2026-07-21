import { StatusPill } from "../../shared/ui";
import { Button, IconButton } from "../../shared/ui-controls";
import { ChannelProductMark } from "./ChannelProductMark";
import type { Channel } from "./types";

export function ChannelDetailHeader({
  channel,
  canEdit,
  canManageLifecycle,
  editing,
  busy,
  onEdit,
  onToggleActive,
  onDelete,
  openChannels,
}: {
  channel: Channel;
  canEdit: boolean;
  canManageLifecycle: boolean;
  editing: boolean;
  busy: boolean;
  onEdit: () => void;
  onToggleActive: () => void;
  onDelete: () => void;
  openChannels: () => void;
}) {
  return (
    <>
      <div className="channel-breadcrumb">
        <button className="link is-muted" type="button" onClick={openChannels}>Каналы</button>
        <span>/</span>
        <strong>{channel.name}</strong>
      </div>

      <div className="channel-detail-header">
        <div>
          <h1>{channel.name}</h1>
          <div className="channel-detail-meta">
            <code>{channel.code}</code>
            <span>·</span>
            {channel.departmentName ?? "Без отдела"}
            <span>·</span>
            <ChannelProductMark product={channel.product} />
          </div>
        </div>
        <div className="channel-detail-actions">
          <StatusPill status={channel.isActive ? "active" : "archived"} />
          {canEdit && !editing && (
            <Button variant="secondary" icon="edit" onClick={onEdit}>Изменить</Button>
          )}
          {canManageLifecycle && (
            <Button variant="secondary" icon="pause" disabled={busy} onClick={onToggleActive}>
              {channel.isActive ? "Деактивировать" : "Активировать"}
            </Button>
          )}
          {canManageLifecycle && (
            <IconButton className="is-danger" icon="trash" label="Удалить канал" onClick={onDelete} />
          )}
        </div>
      </div>
    </>
  );
}
