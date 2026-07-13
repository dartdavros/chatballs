import type { Department, Employee } from "../../types";
import { EmployeeAccessSection } from "./EmployeeAccessSection";
import { EmployeeIdentitySections } from "./EmployeeIdentitySections";
import { EmployeeSecuritySections } from "./EmployeeSecuritySections";
import type { EmployeeForm } from "./model";

export function EmployeeDetailSections({ blocked, departments, employee, form, updateForm }: {
  blocked: boolean;
  departments: Department[];
  employee: Employee;
  form: EmployeeForm;
  updateForm: (field: keyof EmployeeForm, value: string | boolean) => void;
}) {
  return (
    <div className="employee-detail-left">
      <EmployeeIdentitySections departments={departments} employee={employee} form={form} updateForm={updateForm} />
      <EmployeeAccessSection employee={employee} />
      <EmployeeSecuritySections blocked={blocked} employee={employee} form={form} updateForm={updateForm} />
    </div>
  );
}
