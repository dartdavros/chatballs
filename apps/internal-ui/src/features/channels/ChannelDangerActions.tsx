import { Button } from "../../shared/ui-controls";

export function ChannelDangerActions({
  active,
  busy,
  dirty,
  onToggleActive,
  onDelete,
}: {
  active: boolean;
  busy: boolean;
  dirty: boolean;
  onToggleActive: () => void;
  onDelete: () => void;
}) {
  const lifecycleTitle = dirty ? "Сначала сохраните или отмените изменения" : undefined;

  return (
    <footer className="channel-danger-actions">
      <Button variant="secondary" icon="pause" title={lifecycleTitle} disabled={busy || dirty} onClick={onToggleActive}>
        {active ? "Деактивировать" : "Активировать"}
      </Button>
      <Button variant="danger-outline" icon="trash" title={lifecycleTitle} disabled={busy || dirty} onClick={onDelete}>
        Удалить
      </Button>
    </footer>
  );
}
