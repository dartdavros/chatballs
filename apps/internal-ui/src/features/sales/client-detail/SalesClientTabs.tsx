import { clientDetailTabs, type ClientDetailTab } from "./model";

export function SalesClientTabs({ activeTab, setActiveTab }: { activeTab: ClientDetailTab; setActiveTab: (tab: ClientDetailTab) => void }) {
  return (
    <div className="sales-client-detail-tabs">
      {clientDetailTabs.map((tab) => (
        <button className={activeTab === tab.key ? "active" : ""} type="button" onClick={() => setActiveTab(tab.key)} key={tab.key}>{tab.label}</button>
      ))}
    </div>
  );
}
