import type { Employee } from "../../types";
import { Icon } from "../../shared/icons";
import { FormField, SelectField, SwitchButton } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import type { EmployeeForm } from "./model";

export function EmployeeDetailSections({
  blocked,
  currentEmployee,
  details,
  form,
  resetPassword,
  revokeSessions,
  toggleBlocked,
  updateForm,
}: {
  blocked: boolean;
  currentEmployee: Employee;
  details: ReturnType<typeof import("./model").employeeDetails>;
  form: EmployeeForm;
  resetPassword: () => void;
  revokeSessions: () => void;
  toggleBlocked: () => void;
  updateForm: (field: keyof EmployeeForm, value: string | boolean) => void;
}) {
  return (
    <div className="employee-detail-left">
      <section className="employee-detail-card">
        <h3>Основные данные</h3>
        <div className="employee-form-grid">
          <FormField label="Имя" value={form.fullName} onChange={(value) => updateForm("fullName", value)} />
          <FormField label="Должность" value={form.positionTitle} onChange={(value) => updateForm("positionTitle", value)} />
          <FormField label="Телефон" value={form.phone} onChange={(value) => updateForm("phone", value)} />
          <FormField label="Email · используется для входа" value={form.email} onChange={(value) => updateForm("email", value)} mono wide />
        </div>
      </section>

      <section className="employee-detail-card">
        <h3>Роль и доступ</h3>
        <div className="employee-form-grid">
          <SelectField label="Роль" value={form.role} onChange={(value) => updateForm("role", value)} options={[["EMPLOYEE", "Сотрудник"], ["ADMIN", "Администратор"]]} />
          <SelectField label="Отдел" value={form.department} onChange={(value) => updateForm("department", value)} options={[["sales", "Отдел продаж"]]} />
        </div>
        <label className="employee-access-label">Доступные разделы</label>
        <div className="employee-access-list">
          <span className="allowed"><Icon name="check" size={12} />Диалоги</span>
          <span className="allowed"><Icon name="check" size={12} />Клиенты</span>
          <span className="allowed"><Icon name="check" size={12} />Заказы · чтение</span>
          <span>Финансы · нет</span>
          <span>Настройки · нет</span>
        </div>
      </section>

      <section className="employee-detail-card">
        <h3>Безопасность</h3>
        <div className="security-row">
          <div><strong>Пароль</strong><span>Последняя смена: {details.security.passwordChangedAt}</span></div>
          <Button type="button" variant="secondary" onClick={resetPassword}>Сбросить пароль</Button>
        </div>
        <div className="security-row">
          <div><strong>Двухфакторная аутентификация (TOTP)</strong><span>{form.totpEnabled ? "Включена · требуется при каждом входе" : "Отключена для этого сотрудника"}</span></div>
          <SwitchButton checked={form.totpEnabled} className="detail-totp-switch" label="Переключить TOTP" onClick={() => updateForm("totpEnabled", !form.totpEnabled)} />
        </div>
        <div className="security-row last">
          <div><strong>Активные сессии</strong><span>{details.security.sessions}</span></div>
          <Button type="button" variant="secondary" onClick={revokeSessions}>Завершить все</Button>
        </div>
      </section>

      <section className="employee-danger-card">
        <h3>Опасная зона</h3>
        <div>
          <p>{blocked ? "Сотрудник заблокирован и не может войти. Разблокировка восстановит доступ к разделам отдела." : "Блокировка немедленно завершит все сессии и закроет доступ. Активные диалоги вернутся в очередь. Действие требует подтверждения."}</p>
          <Button className="employee-danger-action" type="button" variant="danger-outline" onClick={toggleBlocked} disabled={blocked ? !(currentEmployee.permissions?.canUnblock ?? false) : !(currentEmployee.permissions?.canBlock ?? false)}>{blocked ? "Разблокировать сотрудника" : "Заблокировать сотрудника"}</Button>
        </div>
      </section>
    </div>
  );
}
