import type { Employee, EmployeeGroup, Role } from "../../types";
import { Icon } from "../../shared/icons";
import { groupColorOf } from "../conversations/model";
import type { EmployeeForm } from "./model";

// Основные данные · Должность и группы · Системная роль (кадры E3/E4).
// Владельцу все роли закрыты: роль владельца меняется только передачей владения.

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
  const isOwner = employee.role === "OWNER";

  function toggleGroup(groupId: number) {
    const next = form.groupIds.includes(groupId)
      ? form.groupIds.filter((item) => item !== groupId)
      : [...form.groupIds, groupId];
    updateForm("groupIds", next);
  }

  return (
    <>
      <section className="employee-card">
        <h3>Основные данные</h3>
        <div className="employee-field-grid">
          <EmployeeField label="Имя" value={form.fullName} readOnly={!canProfile} onChange={(value) => updateForm("fullName", value)} />
          <EmployeeField label="Телефон" value={form.phone} readOnly={!canProfile} onChange={(value) => updateForm("phone", value)} />
          <EmployeeField className="is-wide" label="Email · используется для входа" value={form.email} readOnly={!canProfile} mono onChange={(value) => updateForm("email", value)} />
        </div>
      </section>

      <section className="employee-card">
        <h3>Должность и группы</h3>
        <p>Группа задаёт только видимость диалогов и не выдаёт прав.</p>
        <EmployeeField className="is-single" label="Должность" value={form.positionTitle} readOnly={!canProfile} placeholder="напр. Оператор" onChange={(value) => updateForm("positionTitle", value)} />
        {groups.length > 0 ? (
          <div className="employee-group-picks">
            {groups.map((group) => {
              const active = form.groupIds.includes(group.id);
              return (
                <button className={`employee-group-pick ${active ? "is-on" : ""}`} type="button" aria-pressed={active} disabled={!canGroups} onClick={() => toggleGroup(group.id)} key={group.id}>
                  <i>{active && <Icon name="check" size={11} strokeWidth={3} />}</i>
                  <span>
                    <strong><i className="employee-group-dot" style={{ background: groupColorOf(group.id, group.color) }} />{group.name}</strong>
                    <small>{group.memberCount} сотр.</small>
                  </span>
                </button>
              );
            })}
          </div>
        ) : (
          <p className="employee-create-note">Групп пока нет — все сотрудники видят все диалоги.</p>
        )}
      </section>

      <section className="employee-card">
        <h3>Системная роль</h3>
        <p>{isOwner ? "Роль владельца меняется только через передачу владения." : "OWNER и ADMIN идентичны по правам; EMPLOYEE работает только в чате."}</p>
        <div className="employee-choice-list">
          {ROLE_OPTIONS.map((option) => {
            const active = form.role === option.role;
            // Владельца нельзя выбрать ролью: единственный путь — передача владения.
            const locked = isOwner || !canRole || option.role === "OWNER";
            return (
              <button
                className={`employee-choice ${active ? "is-on" : ""} ${locked ? "is-locked" : ""}`}
                type="button"
                disabled={locked}
                onClick={() => updateForm("role", option.role)}
                key={option.role}
              >
                <i>{active && <span />}</i>
                <span>
                  <strong>{option.label}{locked && <Icon name="lock" size={12} strokeWidth={1.8} />}</strong>
                  <small>{option.description}</small>
                </span>
              </button>
            );
          })}
        </div>
      </section>
    </>
  );
}

function EmployeeField({ className = "", label, mono = false, onChange, placeholder = "", readOnly, value }: {
  className?: string;
  label: string;
  mono?: boolean;
  onChange: (value: string) => void;
  placeholder?: string;
  readOnly: boolean;
  value: string;
}) {
  return (
    <label className={`employee-field ${className} ${readOnly ? "is-readonly" : ""}`}>
      <span>{label}</span>
      <input className={mono ? "mono" : ""} value={value} placeholder={placeholder} readOnly={readOnly} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}
