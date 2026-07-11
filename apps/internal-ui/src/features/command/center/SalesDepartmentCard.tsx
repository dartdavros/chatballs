import type { RouteKey } from "../../../types";
import { Icon } from "../../../shared/icons";
import { Button } from "../../../shared/ui-controls";
import type { CommandVm, DepartmentVm } from "./model";
import { MetricGroup } from "./MetricGroup";
import { StatusLabel } from "./StatusLabel";

export function DepartmentsColumn({ setRoute, vm }: { setRoute: (route: RouteKey) => void; vm: CommandVm }) {
  return (
    <section className="command-left">
      <div className="section-head">
        <h2>Отделы</h2>
        <span>{vm.departments.length} активных</span>
      </div>
      {vm.departments.map((department) => (
        <DepartmentCard department={department} periodLabelUpper={vm.periodLabelUpper} setRoute={setRoute} key={department.code} />
      ))}
    </section>
  );
}

function DepartmentCard({ department, periodLabelUpper, setRoute }: { department: DepartmentVm; periodLabelUpper: string; setRoute: (route: RouteKey) => void }) {
  return (
    <article className="sales-card">
      <div className="sales-head">
        <div className="sales-icon"><Icon name={department.icon} size={23} /></div>
        <div className="sales-title">
          <div>
            <h3>{department.name}</h3>
            <StatusLabel status={department.status} />
          </div>
          <p>{department.subtitle}</p>
        </div>
        <Button className="sales-open" icon="arrow" iconSize={16} variant="primary" onClick={() => setRoute(department.route as RouteKey)}>Открыть отдел</Button>
      </div>
      <div className="dept-summary">{department.summary}</div>
      <MetricGroup title="ДИАЛОГИ — СЕЙЧАС" columns={5} items={department.dialogItems} />
      {department.commerceItems && <MetricGroup title={`КОММЕРЦИЯ — ${periodLabelUpper}`} columns={4} items={department.commerceItems} />}
    </article>
  );
}
