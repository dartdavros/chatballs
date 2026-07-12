import type { Employee, RouteKey } from "../../types";
import { Avatar, RoleBadge, StatusPill } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
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
          <p>{form.email} · {form.positionTitle || "Должность не указана"} · {departmentLabel}</p>
        </div>
      </div>
      <div className="employee-header-actions">
        <Button type="button" variant="secondary" onClick={() => setRoute("employees")}>Отмена</Button>
        <Button icon="save" type="button" variant="primary" onClick={saveEmployee} disabled={saving}>{saving ? "Сохранение" : "Сохранить"}</Button>
      </div>
    </section>
  );
}
