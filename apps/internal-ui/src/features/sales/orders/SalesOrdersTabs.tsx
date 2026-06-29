import { UnderlineTabs } from "../../../shared/ui-controls";
import { salesOrderTabs } from "./model";
import type { SalesOrdersTab } from "./types";

export function SalesOrdersTabs({ activeTab, setActiveTab, counts }: { activeTab: SalesOrdersTab; setActiveTab: (tab: SalesOrdersTab) => void; counts: Record<SalesOrdersTab, number> }) {
  const items = salesOrderTabs.map((tab) => ({ ...tab, count: counts[tab.key] }));
  return <UnderlineTabs className="sales-orders-tabs" items={items} value={activeTab} onChange={setActiveTab} />;
}
