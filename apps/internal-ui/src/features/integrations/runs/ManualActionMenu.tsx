import { Dropdown } from "antd";
import { t } from "../../../i18n";
import { Button } from "../../../shared/ui-controls";
import { useConversationRuns } from "./conversationContext";

export function ManualActionMenu() {
  const state = useConversationRuns();
  const actions = state?.catalog?.items;
  if (!state || !actions?.length) return null;
  return <Dropdown overlayClassName="app-dropdown" trigger={["click"]} menu={{ items: actions.map(action => ({
    key: `${action.kind}:${action.id}`, label: action.title, disabled: action.available === false, title: action.reason,
  })), onClick: ({ key }) => { const action = actions.find(item => `${item.kind}:${item.id}` === key); if (action) state.openAction(action); } }}>
    <Button variant="secondary" className="row-menu-button run-launch-trigger" icon="plug">{t("runs.actions")}</Button>
  </Dropdown>;
}
