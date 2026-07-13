import { Icon } from "../../shared/icons";
import type { Employee } from "../../types";

export function EmployeeAccessSection({ employee }: { employee: Employee }) {
  const assignments = employee.accessAssignments ?? [];
  const canChange = employee.permissions?.canChangeAccess ?? false;

  return (
    <section className="employee-detail-card employee-access-card">
      {/* Assignment flow is a design gate: the baseline defines this button, but not its resulting state. */}
      <header><h3>Профили доступа и scopes</h3>{employee.role === "EMPLOYEE" && canChange && <button className="employee-assign-button" type="button"><Icon name="plus" size={14} />Назначить</button>}</header>
      <p>{employee.role === "EMPLOYEE" ? "Рабочий доступ появляется только через активные назначения." : "Роль даёт capability напрямую — назначения не требуются."}</p>
      {employee.role === "EMPLOYEE" && assignments.length > 0 && <div className="employee-assignment-list">{assignments.map((assignment) => <article key={assignment.id}><header><div><i><Icon name="columns" size={15} /></i><span><strong>{assignment.profileName}</strong><small>{assignment.scopeType === "ORGANIZATION" ? "Вся организация" : assignment.departmentName || assignment.departmentCode}</small></span></div><div><b className={assignment.scopeType.toLowerCase()}>{assignment.scopeType === "ORGANIZATION" ? "ОРГАНИЗАЦИЯ" : "ОТДЕЛ"}</b>{canChange && <button aria-label={`Отозвать: ${assignment.profileName}`} type="button"><Icon name="trash" size={15} /></button>}</div></header><footer>{assignment.capabilities?.map((capability) => <code key={capability}>{capability}</code>)}</footer></article>)}</div>}
      {employee.role === "EMPLOYEE" && assignments.length === 0 && <div className="employee-no-access"><Icon name="xCircle" size={17} /><p><strong>Нет рабочего доступа.</strong> У сотрудника нет активных назначений — доступен только разрешённый self-service. Роль EMPLOYEE сама по себе прав не даёт.</p></div>}
      {(employee.role === "ADMIN" || employee.role === "OWNER") && <div className="employee-admin-access-note"><Icon name="warning" size={17} /><p>ADMIN имеет все обычные capability организации без назначений. Профили не ограничивают его полный обычный доступ. Защищённые governance-capability остаются только у OWNER.</p></div>}
    </section>
  );
}
