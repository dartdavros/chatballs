import { Icon } from "../../../shared/icons";
import { t, tn } from "../../../i18n";

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
        <strong>{t("common.selected_count", { count })}</strong>
        <small>{tn("plural.knowledge", count).replace(`${count} `, "")}</small>
      </span>
      <button className="is-primary" disabled={busy} type="button" onClick={onAttach}>
        <Icon name="robot" size={14} strokeWidth={1.9} />{t("ai.attach_agent")}</button>
      <button disabled={busy} type="button" onClick={onMove}>
        <Icon name="move" size={14} strokeWidth={1.9} />{t("ai.move")}</button>
      <button disabled={busy} type="button" onClick={onEnable}>
        <Icon name="eye" size={14} strokeWidth={1.9} />{t("ai.turn")}</button>
      <button disabled={busy} type="button" onClick={onDisable}>
        <Icon name="eyeOff" size={14} strokeWidth={1.9} />{t("ai.turn_off")}</button>
      <button className="is-danger" disabled={busy} type="button" onClick={onRemove}>
        <Icon name="trash" size={14} strokeWidth={1.9} />{t("common.delete")}</button>
      <i className="knowledge-bulk-divider" />
      <button aria-label={t("ai.clear_selection")} className="knowledge-bulk-close" title={t("ai.clear_selection")} type="button" onClick={onClear}>
        <Icon name="close" size={15} strokeWidth={2.2} />
      </button>
    </div>
  );
}
