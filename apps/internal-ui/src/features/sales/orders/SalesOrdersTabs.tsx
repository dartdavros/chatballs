import { UnderlineTabs } from "../../../shared/ui-controls";
import { salesOrderTabs } from "./model";
import type { SalesOrdersTab } from "./types";

export function SalesOrdersTabs({ activeTab, setActiveTab }: { activeTab: SalesOrdersTab; setActiveTab: (tab: SalesOrdersTab) => void }) {
  return <UnderlineTabs className="sales-orders-tabs" items={salesOrderTabs} value={activeTab} onChange={setActiveTab} />;
}
