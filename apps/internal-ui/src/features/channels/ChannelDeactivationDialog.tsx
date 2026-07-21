import { Modal } from "antd";

import { Button } from "../../shared/ui-controls";
import type { Channel } from "./types";

export function ChannelDeactivationDialog({
  channel,
  open,
  busy,
  onConfirm,
  onOpenAgent,
  onClose,
}: {
  channel: Channel;
  open: boolean;
  busy: boolean;
  onConfirm: () => void;
  onOpenAgent: () => void;
  onClose: () => void;
}) {
  return (
    <Modal open={open} onCancel={onClose} footer={null} title="Деактивировать канал?" destroyOnHidden>
      <p className="channel-modal-lead">
        Канал <b>«{channel.name}»</b> перестанет принимать новые диалоги. Активный AI-агент продолжит занимать слот,
        пока вы не остановите его отдельно.
      </p>
      <div className="channel-modal-actions">
        <Button variant="secondary" onClick={onClose}>Отмена</Button>
        <Button variant="secondary" onClick={onOpenAgent}>Открыть агента</Button>
        <Button variant="primary" disabled={busy} onClick={onConfirm}>Деактивировать</Button>
      </div>
    </Modal>
  );
}
