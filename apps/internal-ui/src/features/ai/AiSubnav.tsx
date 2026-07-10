import type { RouteKey } from "../../types";
import { UnderlineTabs } from "../../shared/ui-controls";

const ITEMS: Array<{ key: RouteKey; label: string; disabled?: boolean }> = [
  { key: "aiAgents", label: "AI-агенты" },
  { key: "aiUsage", label: "Использование AI", disabled: true },
];

export function AiSubnav({ route, setRoute }: { route: RouteKey; setRoute: (route: RouteKey) => void }) {
  return (
    <div className="ai-subnav">
      <UnderlineTabs className="ai-subnav-tabs" items={ITEMS} value={route} onChange={setRoute} />
    </div>
  );
}
