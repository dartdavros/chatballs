import { Icon } from "../../../shared/icons";
import type { SalesOverviewVm } from "./model";

export function SalesChart({ vm }: { vm: SalesOverviewVm }) {
  return (
    <section className="sales-chart-card">
      <div className="sales-chart-head">
        <div>
          <h3>Динамика продаж</h3>
          <div>
            <strong>{vm.chartTotal}</strong>
            <span><Icon name="chevron" size={13} />+8%</span>
            <small>чистая выручка · {vm.periodLabel}</small>
          </div>
        </div>
        <em><span />Выручка</em>
      </div>
      <div className="sales-chart-body">
        <svg viewBox="0 0 1000 260" preserveAspectRatio="none">
          <defs>
            <linearGradient id="salesFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#1677ff" stopOpacity="0.16" />
              <stop offset="1" stopColor="#1677ff" stopOpacity="0" />
            </linearGradient>
          </defs>
          {vm.gridLines.map((y) => <line x1="10" x2="990" y1={y} y2={y} stroke="#f2f2f2" strokeWidth="1" vectorEffect="non-scaling-stroke" key={y} />)}
          <path d={vm.areaPath} fill="url(#salesFill)" />
          <path d={vm.linePath} fill="none" stroke="#1677ff" strokeWidth="2.5" vectorEffect="non-scaling-stroke" strokeLinejoin="round" strokeLinecap="round" />
          <circle cx={vm.last.x} cy={vm.last.y} r="4.5" fill="#1677ff" stroke="#ffffff" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />
        </svg>
        <div className="sales-chart-labels">
          {vm.xLabels.map((label) => <span key={label}>{label}</span>)}
        </div>
      </div>
    </section>
  );
}
