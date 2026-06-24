import type { AiAgent } from "./model";

export function AgentsKpiStrip({ agents }: { agents: AiAgent[] }) {
  const active = agents.filter((agent) => agent.isActive).length;
  // Метрики диалогов/конверсии/стоимости появятся с контуром коммуникаций (E05) — пока degraded.
  const cards: Array<{ label: string; value: string }> = [
    { label: "Агентов активно", value: `${active} / ${agents.length}` },
    { label: "Диалогов на AI сейчас", value: "—" },
    { label: "Конверсия AI · сегодня", value: "—" },
    { label: "Стоимость AI · сегодня", value: "—" },
  ];
  return (
    <div className="ai-kpi-strip">
      {cards.map((card) => (
        <div className="ai-kpi-card" key={card.label}>
          <div className="ai-kpi-label">{card.label}</div>
          <div className="ai-kpi-value">{card.value}</div>
        </div>
      ))}
    </div>
  );
}
