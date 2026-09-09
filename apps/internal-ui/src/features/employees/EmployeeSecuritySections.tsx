import { Icon } from "../../shared/icons";
import { SwitchButton } from "../../shared/form-controls";
import type { Employee } from "../../types";
import { formatDate, type EmployeeForm } from "./model";
import { t } from "../../i18n";

// Статус и безопасность · Опасная зона (кадры E3/E4). У владельца единственное
// опасное действие — передача владения: заблокировать или удалить его нельзя.

export function EmployeeSecuritySections({ blocked, employee, form, busy, updateForm, onResetPassword, onTerminateSessions, onToggleBlock, onTransferOwnership }: {
  blocked: boolean;
  employee: Employee;
  form: EmployeeForm;
  busy: boolean;
  updateForm: (field: keyof EmployeeForm, value: string | boolean) => void;
  onResetPassword: () => void;
  onTerminateSessions: () => void;
  onToggleBlock: () => void;
  onTransferOwnership: () => void;
}) {
  const permissions = employee.permissions;
  const isOwner = employee.role === "OWNER";
  const canBlock = blocked ? permissions?.canUnblock : permissions?.canBlock;
  const sessions = employee.activeSessionCount === undefined ? "—" : t("admin.active_devices", { count: employee.activeSessionCount });

  return (
    <>
      <section className="employee-card">
        <h3 className="is-tight">{t("admin.status_security")}</h3>
        <div className="employee-security-row">
          <div>
            <strong>{t("common.password")}</strong>
            <small>{t("admin.last_password_change", { date: formatDate(employee.passwordChangedAt) })}</small>
          </div>
          <button className="employee-security-action" type="button" disabled={busy || !permissions?.canResetPassword} onClick={onResetPassword}>{t("admin.reset_password")}</button>
        </div>
        <div className="employee-security-row">
          <div>
            <strong>{t("admin.two_factor_authentication_totp")}</strong>
            <small>{form.totpEnabled ? t("admin.required_at_every_sign") : t("admin.off_operator")}</small>
          </div>
          <SwitchButton checked={form.totpEnabled} className="ui-switch is-large" label={t("admin.toggle_totp")} disabled={!permissions?.canUpdateProfile} onClick={() => updateForm("totpEnabled", !form.totpEnabled)} />
        </div>
        <div className="employee-security-row is-last">
          <div>
            <strong>{t("common.active_sessions")}</strong>
            <small>{sessions}</small>
          </div>
          <button className="employee-security-action" type="button" disabled={busy || !permissions?.canTerminateSessions} onClick={onTerminateSessions}>{t("admin.end_all")}</button>
        </div>
      </section>

      {(isOwner ? permissions?.canTransferOwnership : canBlock) && (
        <section className="employee-danger">
          <h3>{t("admin.danger_zone")}</h3>
          {isOwner ? (
            <div>
              <strong>{t("admin.ownership_transfer")}</strong>
              <p>{t("admin.ownership_passes_administrator_only_they")}</p>
              <button type="button" disabled={busy} onClick={onTransferOwnership}>
                <Icon name="transfer" size={14} strokeWidth={1.8} />{t("admin.transfer_ownership")}</button>
              <small>{t("admin.owner_cannot_blocked_or_deleted")}</small>
            </div>
          ) : (
            <div>
              <strong>{t("admin.access_block")}</strong>
              <p>
                {blocked
                  ? t("admin.operator_blocked_cannot_sign_unblocking")
                  : t("admin.ends_every_session_immediately_stops")}
              </p>
              <button type="button" disabled={busy} onClick={onToggleBlock}>
                <Icon name="lock" size={14} strokeWidth={1.8} />{blocked ? t("admin.unblock_operator") : t("admin.block_operator")}
              </button>
            </div>
          )}
        </section>
      )}
    </>
  );
}
