import { KeyValue, MetricBox } from "../../shared/form-controls";
import { StatusPill } from "../../shared/ui";
import type { EmployeeStatus } from "./model";

export function EmployeeDetailRail({ details, status }: { details: ReturnType<typeof import("./model").employeeDetails>; status: EmployeeStatus }) {
  return (
    <aside className="employee-detail-rail">
      <section className="employee-detail-card compact">
        <h3>Статус аккаунта</h3>
        <KeyValue label="Статус" value={<StatusPill status={status} />} />
        <KeyValue label="Создан" value={details.account.createdAt} />
        <KeyValue label="Приглашение принято" value={details.account.inviteAcceptedAt} />
        <KeyValue label="Последний вход" value={details.account.lastLogin} />
      </section>

      <section className="employee-detail-card compact">
        <h3>Текущая нагрузка</h3>
        <div className="workload-grid">
          <MetricBox label="Активные диалоги" value={details.workload.activeDialogs} />
          <MetricBox label="В очереди" value={details.workload.queue} />
          <MetricBox label="Продажи · сегодня" value={details.workload.salesToday} />
          <MetricBox label="Ср. ответ" value={details.workload.avgReply} />
        </div>
      </section>

      <section className="employee-detail-card compact">
        <h3>Последние действия</h3>
        <div className="employee-activity-list">
          {details.activity.map((item) => (
            <div key={item.text}>
              <span style={{ background: item.dot }} />
              <p><strong>{item.text}</strong><small>{item.time}</small></p>
            </div>
          ))}
        </div>
      </section>
    </aside>
  );
}
