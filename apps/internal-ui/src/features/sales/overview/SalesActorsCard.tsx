import type { SalesOverviewVm } from "./model";

export function SalesActorsCard({ vm }: { vm: SalesOverviewVm }) {
  return (
    <section className="sales-panel-card sales-actors-card">
      <h3>AI и операторы</h3>
      <SalesActor title="AI-агент" tone="ai" values={[["Диалоги", "35"], ["Продажи", vm.aiSales], ["Конверсия", "13,2%"], ["Стоимость", vm.res.aiCost]]} />
      <SalesActor title="Операторы" tone="operator" values={[["Диалоги", "7"], ["Продажи", vm.opSales], ["Конверсия", "41%"], ["Передано AI→", "4"]]} />
    </section>
  );
}

function SalesActor({ title, tone, values }: { title: string; tone: "ai" | "operator"; values: Array<[string, string]> }) {
  return (
    <div className={`sales-actor ${tone}`}>
      <div className="sales-actor-title"><span><i /></span>{title}</div>
      <div className="sales-actor-grid">
        {values.map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}
      </div>
    </div>
  );
}
