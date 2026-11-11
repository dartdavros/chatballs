import { Icon, LogoSpinner } from "../../../shared/icons";
import { actionCaption } from "./actionPickerModel";
import { ActionSearchText } from "./ActionSearchText";
import type { ManualActionSummary } from "./types";

export function ManualActionItem({ action, search = "", disabled = false, pending = false, onSelect }: {
  action: ManualActionSummary; search?: string; disabled?: boolean; pending?: boolean; onSelect: (action: ManualActionSummary) => void;
}) {
  if (action.available !== true) return null;
  return (
    <button type="button" className="manual-action-item" disabled={disabled} aria-busy={pending || undefined} onClick={() => onSelect(action)}>
      <span className="manual-action-icon" aria-hidden="true">
        <Icon name={action.kind === "scenario" ? "workflow" : "plug"} size={16} />
      </span>
      <span className="manual-action-copy">
        <strong><ActionSearchText text={action.title} search={search} /></strong>
        <small><ActionSearchText text={actionCaption(action)} search={search} /></small>
      </span>
      <span className="manual-action-arrow" aria-hidden="true">{pending ? <LogoSpinner size={16} /> : <Icon name="chevronRight" size={14} />}</span>
    </button>
  );
}
