import { EmptyState } from "../../../shared/ui";

const KPIS = ["Диалоги · 30 дней", "Продажи · 30 дней", "Конверсия", "Стоимость / продажа"];

export function AiAgentMetricsTab() {
  return (
    <div className="ai-agent-metrics">
      <div className="ai-kpi-strip">
        {KPIS.map((label) => (
          <div className="ai-kpi-card" key={label}>
            <div className="ai-kpi-label">{label}</div>
            <div className="ai-kpi-value">—</div>
          </div>
        ))}
      </div>
      <section className="ai-card">
        <h3>Причины передачи оператору · 30 дней</h3>
        <EmptyState title="Данных пока нет" />
      </section>
    </div>
  );
}
