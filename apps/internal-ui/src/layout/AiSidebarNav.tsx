import type { RouteKey } from "../types";

const ITEMS: Array<{
  activeRoutes: RouteKey[];
  disabled?: boolean;
  key: RouteKey;
  label: string;
}> = [
  {
    activeRoutes: ["aiAgents", "aiAgentCreate", "aiAgentDetail"],
    key: "aiAgents",
    label: "AI-агенты",
  },
  {
    activeRoutes: ["aiKnowledge", "aiKnowledgeDetail"],
    key: "aiKnowledge",
    label: "Знания",
  },
  {
    activeRoutes: ["aiUsage"],
    disabled: true,
    key: "aiUsage",
    label: "Использование AI",
  },
];

export function AiSidebarNav({
  route,
  setRoute,
}: {
  route: RouteKey;
  setRoute: (route: RouteKey) => void;
}) {
  return (
    <div className="hub-ai-subnav">
      {ITEMS.map((item) => (
        <button
          className={`hub-ai-nav-item${item.activeRoutes.includes(route) ? " is-active" : ""}`}
          disabled={item.disabled}
          key={item.key}
          type="button"
          onClick={() => setRoute(item.key)}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
