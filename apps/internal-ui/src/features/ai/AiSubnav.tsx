import type { RouteKey } from "../../types";

const TABS: Array<{ key: RouteKey; label: string; available: boolean }> = [
  { key: "aiAgents", label: "AI-агенты", available: true },
  { key: "aiTestChat", label: "Тестовый чат", available: false },
  { key: "aiUsage", label: "Использование AI", available: false },
];

export function AiSubnav({ route, setRoute }: { route: RouteKey; setRoute: (route: RouteKey) => void }) {
  return (
    <div className="ai-subnav">
      {TABS.map((tab) => (
        <button
          key={tab.key}
          type="button"
          className={`ai-subnav-tab ${route === tab.key ? "is-active" : ""}`}
          disabled={!tab.available}
          onClick={() => tab.available && setRoute(tab.key)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
