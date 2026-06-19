import type { RouteKey } from "../../../types";
import { Icon } from "../../../shared/icons";
import { Button } from "../../../shared/ui-controls";
import type { CommandVm } from "./model";
import { MetricGroup } from "./MetricGroup";
import { StatusLabel } from "./StatusLabel";

export function SalesDepartmentCard({ setRoute, vm }: { setRoute: (route: RouteKey) => void; vm: CommandVm }) {
  return (
    <section className="command-left">
      <div className="section-head">
        <h2>Отделы</h2>
        <span>1 активный</span>
      </div>
      <article className="sales-card">
        <div className="sales-head">
          <div className="sales-icon"><Icon name="shop" size={23} /></div>
          <div className="sales-title">
            <div>
              <h3>Продажи</h3>
              <StatusLabel vm={vm} />
            </div>
            <p>Ответственный: Анна Котова · 4 сотрудника · 1 AI-агент</p>
          </div>
          <Button className="sales-open" icon="arrow" iconSize={16} variant="primary" onClick={() => setRoute("salesOverview")}>Открыть отдел</Button>
        </div>
        <div className="dept-summary">{vm.deptSummary}</div>
        <MetricGroup title="ДИАЛОГИ — СЕЙЧАС" columns={5} items={[
          { label: "Открытые диалоги", value: vm.m.open },
          { label: "Активны за 15 мин", value: vm.m.active },
          { label: "На AI", value: vm.m.ai, dot: "#722ed1" },
          { label: "На операторах", value: vm.m.op, dot: "#1677ff" },
          { label: "Ожидают оператора", value: vm.m.wait, color: vm.m.waitColor },
        ]} />
        <MetricGroup title={`КОММЕРЦИЯ — ${vm.periodLabelUpper}`} columns={4} items={[
          { label: "Незавершённые платежи", value: vm.m.pend, color: vm.m.pendColor },
          { label: "Ошибки fulfillment", value: vm.m.ferr, color: vm.m.ferrColor },
          { label: "Продажи", value: vm.m.sales },
          { label: "Чистая выручка", value: vm.m.rev, color: "#389e0d" },
        ]} />
      </article>
    </section>
  );
}
