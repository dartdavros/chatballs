import type { Employee, RouteKey } from "../../types";
import { Icon } from "../../shared/icons";
import { Avatar, RoleBadge, StatusPill } from "../../shared/ui";
import type { EmployeeForm, EmployeeStatus } from "./model";

export function EmployeeDetailHeader({
  employee,
  departmentLabel,
  form,
  saveEmployee,
  saving,
  setRoute,
  status,
}: {
  employee: Employee;
  departmentLabel: string;
  form: EmployeeForm;
  saveEmployee: () => void;
  saving: boolean;
  setRoute: (route: RouteKey) => void;
  status: EmployeeStatus;
}) {
  return (
    <section className="employee-detail-header">
      <div className="employee-detail-main">
        <Avatar employee={employee} />
        <div className="employee-title">
          <div>
            <h1>{form.fullName || form.email}</h1>
            <RoleBadge role={form.role} />
            <StatusPill status={status} />
          </div>
          <p>{form.email} · {departmentLabel}</p>
        </div>
      </div>
      <div className="employee-header-actions">
        <button className="secondary-button" type="button" onClick={() => setRoute("employees")}>Отмена</button>
        <button className="primary-button" type="button" onClick={saveEmployee} disabled={saving}><Icon name="save" size={15} />{saving ? "Сохранение" : "Сохранить"}</button>
      </div>
    </section>
  );
}
