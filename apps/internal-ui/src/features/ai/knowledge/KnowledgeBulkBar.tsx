import { Icon } from "../../../shared/icons";
import { pluralRu } from "../../../shared/utils";

// Панель массовых операций (дизайн-базлайн v2, кадр KB2): тёмная плашка по
// центру снизу, пока живо выделение. Прикрепление к агенту — главное действие.

export function KnowledgeBulkBar({
  busy,
  count,
  onAttach,
  onClear,
  onDisable,
  onEnable,
  onMove,
  onRemove,
}: {
  busy: boolean;
  count: number;
  onAttach: () => void;
  onClear: () => void;
  onDisable: () => void;
  onEnable: () => void;
  onMove: () => void;
  onRemove: () => void;
}) {
  return (
    <div className="knowledge-bulk-bar">
      <span className="knowledge-bulk-count">
        <strong>Выбрано {count}</strong>
        <small>{pluralRu(count, ["знание", "знания", "знаний"]).replace(`${count} `, "")}</small>
      </span>
      <button className="is-primary" disabled={busy} type="button" onClick={onAttach}>
        <Icon name="robot" size={14} strokeWidth={1.9} />Прикрепить к агенту
      </button>
      <button disabled={busy} type="button" onClick={onMove}>
        <Icon name="move" size={14} strokeWidth={1.9} />Переместить
      </button>
      <button disabled={busy} type="button" onClick={onEnable}>
        <Icon name="eye" size={14} strokeWidth={1.9} />Включить
      </button>
      <button disabled={busy} type="button" onClick={onDisable}>
        <Icon name="eyeOff" size={14} strokeWidth={1.9} />Выключить
      </button>
      <button className="is-danger" disabled={busy} type="button" onClick={onRemove}>
        <Icon name="trash" size={14} strokeWidth={1.9} />Удалить
      </button>
      <i className="knowledge-bulk-divider" />
      <button aria-label="Снять выделение" className="knowledge-bulk-close" title="Снять выделение" type="button" onClick={onClear}>
        <Icon name="close" size={15} strokeWidth={2.2} />
      </button>
    </div>
  );
}
