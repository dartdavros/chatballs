import type { RouteKey } from "../../types";
import { UnderlineTabs } from "../../shared/ui-controls";

const ITEMS: Array<{ key: RouteKey; label: string; disabled?: boolean }> = [
  { key: "aiAgents", label: "AI-агенты" },
  { key: "aiTestChat", label: "Тестовый чат", disabled: true },
  { key: "aiUsage", label: "Использование AI", disabled: true },
];

export function AiSubnav({ route, setRoute }: { route: RouteKey; setRoute: (route: RouteKey) => void }) {
  return <UnderlineTabs className="ai-subnav" items={ITEMS} value={route} onChange={setRoute} />;
}
