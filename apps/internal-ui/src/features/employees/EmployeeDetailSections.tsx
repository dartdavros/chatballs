import type { Employee, EmployeeGroup } from "../../types";
import { EmployeeIdentitySections } from "./EmployeeIdentitySections";
import { EmployeeSecuritySections } from "./EmployeeSecuritySections";
import type { EmployeeForm } from "./model";

export function EmployeeDetailSections({ blocked, groups, employee, form, updateForm }: {
  blocked: boolean;
  groups: EmployeeGroup[];
  employee: Employee;
  form: EmployeeForm;
  updateForm: (field: keyof EmployeeForm, value: string | boolean | number[]) => void;
}) {
  return (
    <div className="employee-detail-left">
      <EmployeeIdentitySections groups={groups} employee={employee} form={form} updateForm={updateForm} />
      <EmployeeSecuritySections blocked={blocked} employee={employee} form={form} updateForm={updateForm} />
    </div>
  );
}
