import { Icon } from "../../shared/icons";
import { SwitchButton } from "../../shared/form-controls";
import type { Employee } from "../../types";
import { formatDate, type EmployeeForm } from "./model";

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
  const sessions = employee.activeSessionCount === undefined ? "—" : `${employee.activeSessionCount} устройств`;

  return (
    <>
      <section className="employee-card">
        <h3 className="is-tight">Статус и безопасность</h3>
        <div className="employee-security-row">
          <div>
            <strong>Пароль</strong>
            <small>Последняя смена: {formatDate(employee.passwordChangedAt)} · новый можно отправить письмом или показать и скопировать</small>
          </div>
          <button className="employee-security-action" type="button" disabled={busy || !permissions?.canResetPassword} onClick={onResetPassword}>Сбросить пароль</button>
        </div>
        <div className="employee-security-row">
          <div>
            <strong>Двухфакторная аутентификация (TOTP)</strong>
            <small>{form.totpEnabled ? "Включена · требуется при каждом входе" : "Отключена для этого сотрудника"}</small>
          </div>
          <SwitchButton checked={form.totpEnabled} className="ui-switch is-large" label="Переключить TOTP" disabled={!permissions?.canUpdateProfile} onClick={() => updateForm("totpEnabled", !form.totpEnabled)} />
        </div>
        <div className="employee-security-row is-last">
          <div>
            <strong>Активные сессии</strong>
            <small>{sessions}</small>
          </div>
          <button className="employee-security-action" type="button" disabled={busy || !permissions?.canTerminateSessions} onClick={onTerminateSessions}>Завершить все</button>
        </div>
      </section>

      {(isOwner ? permissions?.canTransferOwnership : canBlock) && (
        <section className="employee-danger">
          <h3>Опасная зона</h3>
          {isOwner ? (
            <div>
              <strong>Передача владения</strong>
              <p>Владение передаётся только администратору: у него уже полный доступ, и после передачи он получит защищённые действия владельца. Операция атомарна, аудируется и требует подтверждения.</p>
              <button type="button" disabled={busy} onClick={onTransferOwnership}>
                <Icon name="transfer" size={14} strokeWidth={1.8} />Передать владение
              </button>
              <small>Владельца нельзя заблокировать или удалить, поэтому других опасных действий на его карточке нет.</small>
            </div>
          ) : (
            <div>
              <strong>Блокировка доступа</strong>
              <p>
                {blocked
                  ? "Сотрудник заблокирован и не может войти. Разблокировка восстановит доступ по активным назначениям."
                  : "Немедленно завершит все сессии и прекратит HTTP и realtime actions. Аудит и авторство сохраняются. Требует подтверждения."}
              </p>
              <button type="button" disabled={busy} onClick={onToggleBlock}>
                <Icon name="lock" size={14} strokeWidth={1.8} />{blocked ? "Разблокировать сотрудника" : "Заблокировать сотрудника"}
              </button>
            </div>
          )}
        </section>
      )}
    </>
  );
}
