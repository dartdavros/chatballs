import { DecisionDialog } from "../../shared/DecisionDialog";
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
    <DecisionDialog
      open={open}
      onClose={onClose}
      tone="danger"
      icon="trash"
      title={blockers ? "Канал нельзя удалить" : "Удалить канал?"}
      description={blockers
        ? "Есть связанные записи. Вместо удаления используйте деактивацию — история сохранится."
        : <>Канал <b>«{channel.name}»</b> будет удалён безвозвратно.</>}
      width={566}
      actions={blockers ? <>
        <Button variant="secondary" onClick={onClose}>Закрыть</Button>
        {channel.isActive && <Button className="channel-warning-action" variant="secondary" disabled={busy} onClick={onDeactivate}>Деактивировать вместо удаления</Button>}
      </> : <>
        <Button variant="secondary" onClick={onClose}>Отмена</Button>
        <Button variant="danger-outline" icon="trash" disabled={busy} onClick={onConfirm}>Удалить канал</Button>
      </>}
    >
      {blockers ? (
        <>
          <div className="channel-section-eyebrow">БЛОКИРУЮЩИЕ СВЯЗИ</div>
          <div className="channel-blockers-list">
            {blockers.map((item) => (
              <div key={item.type}>
                <span>{BLOCKER_LABELS[item.type] ?? "Связанная запись"}</span>
                <b>{item.count}</b>
              </div>
            ))}
          </div>
        </>
      ) : (
        <p className="channel-delete-note">Если у канала есть диалоги, заказы или подключения, удаление не выполнится. Деактивация сохраняет историю и отключает канал от новых диалогов.</p>
      )}
    </DecisionDialog>
  );
}
