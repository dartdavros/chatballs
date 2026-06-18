import { salesOrderTabs } from "./model";
import type { SalesOrdersTab } from "./types";

export function SalesOrdersTabs({ activeTab, setActiveTab }: { activeTab: SalesOrdersTab; setActiveTab: (tab: SalesOrdersTab) => void }) {
  return (
    <div className="sales-orders-tabs">
      {salesOrderTabs.map((tab) => (
        <button className={activeTab === tab.key ? "active" : ""} type="button" onClick={() => setActiveTab(tab.key)} key={tab.key}>
          {tab.label} <span>{tab.count}</span>
        </button>
      ))}
    </div>
  );
}
