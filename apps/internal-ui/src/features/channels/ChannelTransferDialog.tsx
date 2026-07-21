import { Modal } from "antd";

import { Button } from "../../shared/ui-controls";
import { ChannelBadge } from "./ChannelBadge";
import type { ConnectionTransfer } from "./channel-connection-types";

export function ChannelTransferDialog({ transfer, channelName, busy, onConfirm, onClose }: { transfer: ConnectionTransfer | null; channelName: string; busy: boolean; onConfirm: () => void; onClose: () => void }) {
  return (
    <Modal open={transfer !== null} onCancel={onClose} footer={null} title="Перенести подключение в этот канал?" destroyOnHidden>
      {transfer && <>
        <p className="channel-modal-lead">Подключение <b>«{transfer.integration.name}»</b> уже используется каналом <b>«{transfer.fromChannel}»</b>. После переноса новые обращения пойдут в выбранный канал.</p>
        <div className="channel-transfer-path"><ChannelBadge provider={transfer.integration.provider} /><span>{transfer.fromChannel}</span><i>→</i><b>{channelName}</b></div>
        <p className="channel-muted">Существующие диалоги остаются в прежнем канале.</p>
        <div className="channel-modal-actions"><Button variant="secondary" onClick={onClose}>Отмена</Button><Button variant="primary" disabled={busy} onClick={onConfirm}>Перенести подключение</Button></div>
      </>}
    </Modal>
  );
}
