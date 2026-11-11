import { useId } from "react";
import { fmt, t, tn } from "../../../i18n";
import { Icon } from "../../../shared/icons";
import { actionKey, isActionGroupOpen, type ActionPickerGroup } from "./actionPickerModel";
import { ActionSearchText } from "./ActionSearchText";
import { ManualActionItem } from "./ManualActionItem";
import type { ManualActionSummary } from "./types";

type Props = {
  groups: ActionPickerGroup[]; search: string; expanded: ReadonlySet<string>; collapsedSearch: ReadonlySet<string>;
  pendingKey: string | null; onToggle: (key: string) => void; onSelect: (action: ManualActionSummary) => void;
};

export function ActionPickerTree(props: Props) {
  const id = useId();
  const renderGroup = (group: ActionPickerGroup, depth: number) => {
    const open = isActionGroupOpen(group.key, props.search, props.expanded, props.collapsedSearch);
    const childrenId = `${id}-${encodeURIComponent(group.key)}`;
    return <li className={depth === 0 ? "manual-action-root" : undefined} key={group.key}>
      <button type="button" className={`manual-action-group${depth === 0 ? " is-root" : ""}`} aria-expanded={open} aria-controls={childrenId}
        onClick={() => props.onToggle(group.key)}>
        <span className="manual-action-chevron"><Icon name="chevronRight" size={14} /></span>
        <span className={depth === 0 ? "manual-action-group-symbol" : "manual-action-icon"}>
          <Icon name={depth > 0 ? "folder" : group.sourceKind === "scenarios" ? "workflow" : "plug"} size={16} />
        </span>
        <span className="manual-action-group-label"><ActionSearchText text={group.title} search={props.search} />
          {group.subtitle && <small><ActionSearchText text={group.subtitle} search={props.search} /></small>}</span>
        <span className="manual-action-count" aria-label={tn("run_action_picker.count", group.count)}>{fmt.number(group.count)}</span>
      </button>
      <ul className="manual-action-children" id={childrenId} hidden={!open}>
        {open && <>{group.groups.map(child => renderGroup(child, depth + 1))}
          {group.actions.map(action => <li key={actionKey(action)}><ManualActionItem action={action} search={props.search}
            disabled={props.pendingKey !== null} pending={props.pendingKey === actionKey(action)} onSelect={props.onSelect} /></li>)}</>}
      </ul>
    </li>;
  };
  return <ul className="manual-action-tree" aria-label={t("run_action_picker.actions")}>{props.groups.map(group => renderGroup(group, 0))}</ul>;
}
