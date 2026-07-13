import { Icon } from "../../shared/icons";
import { SwitchButton } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import type { Employee } from "../../types";
import type { EmployeeForm } from "./model";

export function EmployeeSecuritySections({ blocked, employee, form, updateForm }: {
  blocked: boolean;
  employee: Employee;
  form: EmployeeForm;
  updateForm: (field: keyof EmployeeForm, value: string | boolean) => void;
}) {
  // Confirmation/result states for security commands are absent from the approved baseline.
  const permissions = employee.permissions;
  const canToggle = blocked ? permissions?.canUnblock : permissions?.canBlock;
  return <>
    <section className="employee-detail-card employee-security-card">
      <h3>Статус и безопасность</h3>
      <div className="security-row"><div><strong>Пароль</strong><span>Последняя смена: —</span></div><Button type="button" variant="secondary" disabled={!permissions?.canResetPassword}>Сбросить пароль</Button></div>
      <div className="security-row"><div><strong>Двухфакторная аутентификация (TOTP)</strong><span>{form.totpEnabled ? "Включена · требуется при каждом входе" : "Отключена для этого сотрудника"}</span></div><SwitchButton checked={form.totpEnabled} className="detail-totp-switch" label="Переключить TOTP" disabled={!permissions?.canUpdateProfile} onClick={() => updateForm("totpEnabled", !form.totpEnabled)} /></div>
      <div className="security-row last"><div><strong>Активные сессии</strong><span>{employee.activeSessionCount === undefined ? "—" : `${employee.activeSessionCount} устройств`}</span></div><Button type="button" variant="secondary" disabled={!permissions?.canTerminateSessions}>Завершить все</Button></div>
    </section>
    {canToggle && <section className="employee-danger-card"><h3>Опасная зона</h3><div><p>{blocked ? "Сотрудник заблокирован и не может войти. Разблокировка восстановит доступ по активным назначениям." : "Блокировка немедленно завершит все сессии и прекратит HTTP и realtime actions. Аудит и авторство сохраняются. Требует подтверждения."}</p><Button className="employee-danger-action" type="button" variant="danger-outline">{blocked ? "Разблокировать сотрудника" : "Заблокировать сотрудника"}</Button></div></section>}
  </>;
}
