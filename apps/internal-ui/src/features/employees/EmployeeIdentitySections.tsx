import type { Department, Employee, Role } from "../../types";
import { FormField, SelectField } from "../../shared/form-controls";
import { Icon } from "../../shared/icons";
import type { EmployeeForm } from "./model";

const ROLE_OPTIONS: Array<{ role: Role; label: string; description: string }> = [
  { role: "OWNER", label: "Владелец", description: "Полный доступ. Ровно один в организации. Изменяется только через передачу владения." },
  { role: "ADMIN", label: "Администратор", description: "Все обычные capability. Не управляет владельцем и другими администраторами." },
  { role: "EMPLOYEE", label: "Сотрудник", description: "Доступ только через назначенные профили и scopes." },
];

export function EmployeeIdentitySections({ departments, employee, form, updateForm }: {
  departments: Department[];
  employee: Employee;
  form: EmployeeForm;
  updateForm: (field: keyof EmployeeForm, value: string | boolean) => void;
}) {
  const canProfile = employee.permissions?.canUpdateProfile ?? false;
  const canPlacement = employee.permissions?.canChangePlacement ?? false;
  const canRole = employee.permissions?.canChangeRole ?? false;
  return <>
    <section className="employee-detail-card"><h3>Основные данные</h3><div className="employee-form-grid"><FormField disabled={!canProfile} label="Имя" value={form.fullName} onChange={(value) => updateForm("fullName", value)} /><FormField disabled={!canProfile} label="Телефон" value={form.phone} onChange={(value) => updateForm("phone", value)} /><FormField disabled={!canProfile} label="Email · используется для входа" value={form.email} onChange={(value) => updateForm("email", value)} mono wide /></div></section>
    <section className="employee-detail-card employee-placement-card"><h3>Должность и размещение</h3><p>Оргструктура. Не выдаёт прав доступа.</p><div className="employee-form-grid"><FormField disabled={!canProfile} label="Должность ·" value={form.positionTitle} onChange={(value) => updateForm("positionTitle", value)} placeholder="напр. Менеджер по продажам" /><SelectField disabled={!canPlacement || employee.role === "OWNER"} label="Основной отдел" value={form.department} onChange={(value) => updateForm("department", value)} options={[["", "Верхний уровень компании"], ...departments.map((department) => [department.code, department.name] as [string, string])]} /></div>{employee.role === "OWNER" && <small>Владелец всегда находится на уровне компании — отдел назначить нельзя.</small>}</section>
    <section className="employee-detail-card employee-role-card"><h3>Системная роль</h3><p>Уровень в административной иерархии. {employee.role === "OWNER" ? "Роль владельца меняется только через передачу владения." : "Не выводится из должности или отдела."}</p><div>{ROLE_OPTIONS.map((option) => { const active = form.role === option.role; const disabled = !canRole || option.role === "OWNER"; return <button className={active ? "active" : ""} type="button" disabled={disabled} onClick={() => updateForm("role", option.role)} key={option.role}><i>{active && <span />}</i><span><strong>{option.label}{option.role === "OWNER" && <Icon name="lock" size={12} />}</strong><small>{option.description}</small></span></button>; })}</div></section>
  </>;
}
