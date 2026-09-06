import type { Employee, RouteKey } from "../../types";
import { Icon } from "../../shared/icons";
import { Avatar } from "../../shared/ui";
import { BackLink, Button } from "../../shared/ui-controls";
import { employeeAvatarColor, groupsLabel, roleBadge, statusBadge, type EmployeeForm } from "./model";

// Шапка карточки сотрудника (дизайн-базлайн v2, кадры E3/E4): аватар 60px,
// имя, бейджи роли и статуса, строка «email · должность · группы».
// У владельца правки закрыты — вместо кнопок «Только просмотр».

export function EmployeeDetailHeader({ employee, form, saveEmployee, saving, setRoute }: {
  employee: Employee;
  form: EmployeeForm;
  saveEmployee: () => void;
  saving: boolean;
  setRoute: (route: RouteKey) => void;
}) {
  const editable = employee.permissions?.canUpdateProfile ?? false;
  const role = roleBadge(form.role);
  const status = statusBadge(employee);

  return (
    <>
      <BackLink label="Все сотрудники" onClick={() => setRoute("employees")} />
      <header className="employee-head">
        <Avatar employee={employee} background={employeeAvatarColor(employee)} />
        <div className="employee-head-text">
          <div>
            <h2>{form.fullName || form.email}</h2>
            <b className="employees-badge" style={{ background: role.bg, color: role.color }}>{role.text}</b>
            <b className="employees-badge has-dot" style={{ background: status.bg, color: status.color }}><i />{status.text}</b>
          </div>
          <p><span>{form.email}</span> · {form.positionTitle} · {groupsLabel(employee)}</p>
        </div>
        <div className="employee-head-actions">
          {editable ? (
            <>
              <Button variant="secondary" type="button" onClick={() => setRoute("employees")}>Отмена</Button>
              <Button variant="primary" type="button" icon="save" iconSize={15} disabled={saving} onClick={saveEmployee}>
                {saving ? "Сохранение" : "Сохранить"}
              </Button>
            </>
          ) : (
            <span className="employee-readonly-label"><Icon name="lock" size={14} strokeWidth={1.8} />Только просмотр</span>
          )}
        </div>
      </header>
    </>
  );
}
