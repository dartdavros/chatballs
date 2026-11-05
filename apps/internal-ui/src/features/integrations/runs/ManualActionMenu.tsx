import { Dropdown } from "antd";
import { t } from "../../../i18n";
import { Button } from "../../../shared/ui-controls";
import { useConversationRuns } from "./conversationContext";
import { ManualActionItem } from "./ManualActionItem";
import "./manual-action-menu.css";

export function ManualActionMenu() {
  const state = useConversationRuns();
  const actions = state?.catalog?.items;
  if (!state || state.loading || state.error || !actions?.length) return null;
  return (
    <Dropdown overlayClassName="app-dropdown is-manual-actions" trigger={["click"]}
      align={{ overflow: { shiftY: true } }} menu={{
        items: [{ type: "group", label: t("runs.context_actions"), children: actions.map(action => ({
          key: `${action.kind}:${action.id}`,
          label: <ManualActionItem action={action} />,
          disabled: action.available === false,
        })) }],
        onClick: ({ key }) => {
          const action = actions.find(item => `${item.kind}:${item.id}` === key);
          if (action && action.available !== false) state.openAction(action);
        },
      }}>
      <Button variant="secondary" className="row-menu-button run-launch-trigger" icon="plug"
        aria-label={t("runs.actions")}>
        <span className="run-launch-label">{t("runs.actions")}</span>
      </Button>
    </Dropdown>
  );
}
