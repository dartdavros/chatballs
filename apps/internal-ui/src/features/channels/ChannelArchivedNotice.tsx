import { Button } from "../../shared/ui-controls";

/** Архивный канал: что это значит и как вернуть в работу. */
export function ChannelArchivedNotice({ canManage, busy, onActivate }: { canManage: boolean; busy: boolean; onActivate: () => void }) {
  return (
    <div className="channel-notice">
      <div>
        <strong>Канал архивный</strong>
        <p>
          Не принимает новые диалоги и не выбирается при привязке подключения.
          История диалогов сохранена и доступна.
        </p>
      </div>
      {canManage && (
        <Button variant="secondary" disabled={busy} onClick={onActivate}>Активировать</Button>
      )}
    </div>
  );
}
