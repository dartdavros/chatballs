import type { Employee, EmployeeGroup, Role } from "../../types";
import { FormField } from "../../shared/form-controls";
import { Icon } from "../../shared/icons";
import type { EmployeeForm } from "./model";

const ROLE_OPTIONS: Array<{ role: Role; label: string; description: string }> = [
  { role: "OWNER", label: "Владелец", description: "Полный доступ. Ровно один в организации. Изменяется только через передачу владения." },
  { role: "ADMIN", label: "Администратор", description: "Полный доступ, идентичен владельцу. Единственное отличие владельца — его нельзя удалить." },
  { role: "EMPLOYEE", label: "Сотрудник", description: "Работает в чате. Видит диалоги своих групп, диалоги без группы и назначенные ему." },
];

export function EmployeeIdentitySections({ groups, employee, form, updateForm }: {
  groups: EmployeeGroup[];
  employee: Employee;
  form: EmployeeForm;
  updateForm: (field: keyof EmployeeForm, value: string | boolean | number[]) => void;
}) {
  const canProfile = employee.permissions?.canUpdateProfile ?? false;
  const canGroups = employee.permissions?.canChangeGroups ?? false;
  const canRole = employee.permissions?.canChangeRole ?? false;

  function toggleGroup(groupId: number) {
    const next = form.groupIds.includes(groupId)
      ? form.groupIds.filter((item) => item !== groupId)
      : [...form.groupIds, groupId];
    updateForm("groupIds", next);
  }

  return <>
    <section className="employee-detail-card"><h3>Основные данные</h3><div className="employee-form-grid"><FormField disabled={!canProfile} label="Имя" value={form.fullName} onChange={(value) => updateForm("fullName", value)} /><FormField disabled={!canProfile} label="Телефон" value={form.phone} onChange={(value) => updateForm("phone", value)} /><FormField disabled={!canProfile} label="Email · используется для входа" value={form.email} onChange={(value) => updateForm("email", value)} mono wide /></div></section>
    <section className="employee-detail-card employee-placement-card"><h3>Должность и группы</h3><p>Группа задаёт только видимость диалогов и не выдаёт прав.</p><div className="employee-form-grid"><FormField disabled={!canProfile} label="Должность" value={form.positionTitle} onChange={(value) => updateForm("positionTitle", value)} placeholder="напр. Оператор" wide /></div>{groups.length ? <div className="employee-create-profiles">{groups.map((group) => { const active = form.groupIds.includes(group.id); return <label className={active ? "selected" : ""} key={group.id}><button type="button" aria-pressed={active} disabled={!canGroups} onClick={() => toggleGroup(group.id)}><i>{active && <Icon name="check" size={11} />}</i><span><strong>{group.name}</strong><small>{group.memberCount} сотр.</small></span></button></label>; })}</div> : <small>Групп пока нет — все сотрудники видят все диалоги.</small>}</section>
    <section className="employee-detail-card employee-role-card"><h3>Системная роль</h3><p>{employee.role === "OWNER" ? "Роль владельца меняется только через передачу владения." : "OWNER и ADMIN идентичны по правам; EMPLOYEE работает только в чате."}</p><div>{ROLE_OPTIONS.map((option) => { const active = form.role === option.role; const disabled = !canRole || option.role === "OWNER"; return <button className={active ? "active" : ""} type="button" disabled={disabled} onClick={() => updateForm("role", option.role)} key={option.role}><i>{active && <span />}</i><span><strong>{option.label}{option.role === "OWNER" && <Icon name="lock" size={12} />}</strong><small>{option.description}</small></span></button>; })}</div></section>
  </>;
}
