import { useState } from "react";

import { t } from "../../i18n";
import { DecisionDialog } from "../../shared/DecisionDialog";
import { Button } from "../../shared/ui-controls";
import type { Employee } from "../../types";
import { dismissEmployee } from "./api";
import "./styles-dismissal.css";

export function EmployeeDismissDialog({ employee, onClose, onDismissed }: {
  employee: Employee;
  onClose: () => void;
  onDismissed: (employee: Employee) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (employee.role === "OWNER" || !employee.permissions?.canDismiss) return null;

  async function confirm() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      onDismissed(await dismissEmployee(employee.id));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("common.could_not_complete_action"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <DecisionDialog open centered width={460} className="employee-dismiss-dialog"
      tone="danger" icon="errorCircle" title={t("employees.dismiss_title")}
      onClose={() => { if (!busy) onClose(); }}
      description={<>
        {t("employees.dismiss_description", { name: employee.fullName || employee.email })}
        <span className="employee-dismiss-error" role="alert">{error}</span>
      </>}
      actions={<>
        <Button variant="secondary" disabled={busy} onClick={onClose}>{t("common.cancel")}</Button>
        <Button variant="danger-outline" disabled={busy} aria-busy={busy} onClick={() => void confirm()}>
          {t("employees.dismiss")}
        </Button>
      </>} />
  );
}
