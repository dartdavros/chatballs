import type { Employee, RouteKey } from "../../types";
import { Icon } from "../../shared/icons";
import { Avatar, RoleBadge, StatusPill } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import { groupsLabel, type EmployeeForm, type EmployeeStatus } from "./model";

export function EmployeeDetailHeader({ employee, form, saveEmployee, saving, setRoute, status }: {
  employee: Employee;
  form: EmployeeForm;
  saveEmployee: () => void;
  saving: boolean;
  setRoute: (route: RouteKey) => void;
  status: EmployeeStatus;
}) {
  const editable = employee.permissions?.canUpdateProfile ?? false;
  return <>
    <button className="link is-muted has-icon" type="button" onClick={() => setRoute("employees")}><Icon name="arrow" size={15} />Все сотрудники</button>
    <section className="employee-detail-header">
      <div className="employee-detail-main">
        <Avatar employee={employee} />
        <div className="employee-title"><div><h1>{form.fullName || form.email}</h1><RoleBadge role={form.role} /><StatusPill status={status} /></div><p><span className="employee-title-email">{form.email}</span> · {form.positionTitle} · {groupsLabel(employee)}</p></div>
      </div>
      <div className="employee-header-actions">
        {!editable ? <span className="employee-readonly-label"><Icon name="lock" size={14} />Только просмотр</span> : <><Button type="button" variant="secondary" onClick={() => setRoute("employees")}>Отмена</Button><Button icon="save" type="button" variant="primary" onClick={saveEmployee} disabled={saving}>{saving ? "Сохранение" : "Сохранить"}</Button></>}
      </div>
    </section>
  </>;
}
