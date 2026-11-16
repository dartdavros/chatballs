import { DecisionDialog } from "../../../shared/DecisionDialog";
import { Button } from "../../../shared/ui-controls";
import { et } from "./copy";

export type Confirmation = "disable" | "rotate" | "revoke";
export function SettingsConfirmation({ action, busy, cancel, confirm }: {
  action: Confirmation; busy: boolean; cancel: () => void; confirm: () => void;
}) {
  return <DecisionDialog open onClose={cancel} tone={action === "revoke" ? "danger" : "warning"}
    icon={action === "revoke" ? "errorCircle" : "alert"} title={et(`policy.${action}Title`)} description={et(`policy.${action}Lead`)}
    actions={<><Button variant="secondary" disabled={busy} onClick={cancel}>{et("settings.cancel")}</Button>
      <Button variant={action === "revoke" ? "danger-outline" : "primary"} disabled={busy} onClick={confirm}>{et(`policy.${action}Action`)}</Button></>}>
    <div className="settings-risk-note"><p>{et(`policy.${action}Risk`)}</p></div>
  </DecisionDialog>;
}
