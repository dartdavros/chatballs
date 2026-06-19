import { UnderlineTabs } from "../../../shared/ui-controls";
import { clientDetailTabs, type ClientDetailTab } from "./model";

export function SalesClientTabs({ activeTab, setActiveTab }: { activeTab: ClientDetailTab; setActiveTab: (tab: ClientDetailTab) => void }) {
  return <UnderlineTabs className="sales-client-detail-tabs" items={clientDetailTabs} value={activeTab} onChange={setActiveTab} />;
}
