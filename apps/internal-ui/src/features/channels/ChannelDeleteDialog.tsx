import { Modal } from "antd";

import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { BLOCKER_LABELS } from "./model";
import type { Channel, DeletionBlocker } from "./types";

/**
 * Удаление канала: подтверждение, а при связанных записях — их список.
 *
 * Backend отвечает блокерами вместо удаления, поэтому диалог не закрывается,
 * а переключается на объяснение и предлагает деактивацию.
 */
export function ChannelDeleteDialog({
  channel,
  open,
  blockers,
  busy,
  onConfirm,
  onDeactivate,
  onClose,
}: {
  channel: Channel;
  open: boolean;
  blockers: DeletionBlocker[] | null;
  busy: boolean;
  onConfirm: () => void;
  onDeactivate: () => void;
  onClose: () => void;
}) {
  return (
    <Modal
      className="channel-delete-modal"
      open={open}
      onCancel={onClose}
      footer={null}
      title={blockers ? "Канал нельзя удалить" : "Удалить канал?"}
      destroyOnHidden
    >
      {blockers ? (
        <>
          <p className="channel-modal-lead">
            Есть связанные записи. Вместо удаления используйте деактивацию — история сохранится.
          </p>
          <div className="channel-section-eyebrow">БЛОКИРУЮЩИЕ СВЯЗИ</div>
          <div className="channel-blockers-list">
            {blockers.map((item) => (
              <div key={item.type}>
                <span>{BLOCKER_LABELS[item.type] ?? "Связанная запись"}</span>
                <b>{item.count}</b>
              </div>
            ))}
          </div>
          <div className="channel-modal-actions">
            <Button variant="secondary" onClick={onClose}>Закрыть</Button>
            {channel.isActive && (
              <Button variant="primary" disabled={busy} onClick={onDeactivate}>
                Деактивировать вместо удаления
              </Button>
            )}
          </div>
        </>
      ) : (
        <>
          <p className="channel-modal-lead">
            Канал <b>«{channel.name}»</b> будет удалён безвозвратно. Если у канала есть диалоги,
            заказы или подключения, удаление не выполнится — их придётся снять или деактивировать канал.
          </p>
          <div className="channel-modal-actions">
            <Button variant="secondary" onClick={onClose}>Отмена</Button>
            <Button variant="danger-outline" icon="trash" disabled={busy} onClick={onConfirm}>
              Удалить канал
            </Button>
          </div>
        </>
      )}
      {!blockers && (
        <p className="channel-modal-hint">
          <Icon name="warning" size={14} />
          Деактивация сохраняет историю и отключает канал от новых диалогов.
        </p>
      )}
    </Modal>
  );
}
