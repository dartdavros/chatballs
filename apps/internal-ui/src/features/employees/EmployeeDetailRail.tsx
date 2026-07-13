import type { Employee } from "../../types";
import { KeyValue } from "../../shared/form-controls";
import { StatusPill } from "../../shared/ui";
import { auditItem, employeeStatusKey, formatDate, formatLastLogin } from "./model";

const ROLE_LABELS = { OWNER: "Владелец", ADMIN: "Администратор", EMPLOYEE: "Сотрудник" } as const;

export function EmployeeDetailRail({ employee }: { employee: Employee }) {
  const audit = (employee.auditEvents ?? []).map(auditItem);
  return (
    <aside className="employee-detail-rail">
      <section className="employee-detail-card compact">
        <h3>Учётная запись</h3>
        <KeyValue label="Статус" value={<StatusPill status={employeeStatusKey(employee)} />} />
        <KeyValue label="Роль" value={ROLE_LABELS[employee.role]} />
        <KeyValue label="Создан" value={formatDate(employee.createdAt)} />
        <KeyValue label="Последний вход" value={formatLastLogin(employee.lastLogin)} />
      </section>
      <section className="employee-detail-card compact">
        <h3>Аудит</h3>
        <div className="employee-activity-list">
          {audit.map((item, index) => <div key={`${item.code}-${index}`}><span style={{ background: item.dot }} /><p><strong>{item.text}</strong><small>{item.code} · {item.time}</small></p></div>)}
        </div>
      </section>
    </aside>
  );
}
