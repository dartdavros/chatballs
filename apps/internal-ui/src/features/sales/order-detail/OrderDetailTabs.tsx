import { UnderlineTabs } from "../../../shared/ui-controls";
import { orderDetailTabs, type OrderDetailTab } from "./model";

export function OrderDetailTabs({ activeTab, setActiveTab }: { activeTab: OrderDetailTab; setActiveTab: (tab: OrderDetailTab) => void }) {
  return <UnderlineTabs className="order-detail-tabs" items={orderDetailTabs} value={activeTab} onChange={setActiveTab} />;
}
