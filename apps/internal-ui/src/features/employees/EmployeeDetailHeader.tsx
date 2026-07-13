import type { Department, Employee, RouteKey } from "../../types";
import { Icon } from "../../shared/icons";
import { Avatar, RoleBadge, StatusPill } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import { departmentLabel, type EmployeeForm, type EmployeeStatus } from "./model";

export function EmployeeDetailHeader({ departments, employee, form, saveEmployee, saving, setRoute, status }: {
  departments: Department[];
  employee: Employee;
  form: EmployeeForm;
  saveEmployee: () => void;
  saving: boolean;
  setRoute: (route: RouteKey) => void;
  status: EmployeeStatus;
}) {
  const editable = employee.permissions?.canUpdateProfile ?? false;
  return <>
    <button className="employee-back-link" type="button" onClick={() => setRoute("employees")}><Icon name="arrow" size={15} />Все сотрудники</button>
    <section className="employee-detail-header">
      <div className="employee-detail-main">
        <Avatar employee={employee} />
        <div className="employee-title"><div><h1>{form.fullName || form.email}</h1><RoleBadge role={form.role} /><StatusPill status={status} /></div><p><span className="employee-title-email">{form.email}</span> · {form.positionTitle} · {departmentLabel({ ...employee, department: form.department || null }, departments)}</p></div>
      </div>
      <div className="employee-header-actions">
        {!editable ? <span className="employee-readonly-label"><Icon name="lock" size={14} />Только просмотр</span> : <><Button type="button" variant="secondary" onClick={() => setRoute("employees")}>Отмена</Button><Button icon="save" type="button" variant="primary" onClick={saveEmployee} disabled={saving}>{saving ? "Сохранение" : "Сохранить"}</Button></>}
      </div>
    </section>
  </>;
}
