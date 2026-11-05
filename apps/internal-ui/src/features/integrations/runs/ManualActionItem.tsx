import { t } from "../../../i18n";
import { Icon } from "../../../shared/icons";
import type { ManualAction } from "./types";

export function ManualActionItem({ action }: { action: ManualAction }) {
  const unavailable = action.available === false;
  const subtitle = unavailable
    ? action.reason || t("runs.unavailable")
    : [t(action.kind === "scenario" ? "runs.scenario" : "runs.operation"), action.connection,
      action.readOnly ? t("runs.read_only") : null].filter(Boolean).join(" · ");

  return (
    <button type="button" className="manual-action-item" tabIndex={-1} disabled={unavailable}>
      <span className="manual-action-icon" aria-hidden="true">
        <Icon name={action.kind === "scenario" ? "list" : "plug"} size={14} />
      </span>
      <span className="manual-action-copy">
        <strong>{action.title}</strong>
        <small>{subtitle}</small>
      </span>
    </button>
  );
}
