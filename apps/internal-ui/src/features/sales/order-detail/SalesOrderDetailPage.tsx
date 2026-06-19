import { useState } from "react";

import type { RouteKey } from "../../../types";
import { OrderAuditTab } from "./OrderAuditTab";
import { OrderDetailHeader } from "./OrderDetailHeader";
import { OrderDetailTabs } from "./OrderDetailTabs";
import { OrderFulfillmentTab } from "./OrderFulfillmentTab";
import { OrderPaymentsTab } from "./OrderPaymentsTab";
import { OrderReceiptsTab } from "./OrderReceiptsTab";
import { OrderSubscriptionTab } from "./OrderSubscriptionTab";
import { OrderSummaryTab } from "./OrderSummaryTab";
import { OrderTimeline } from "./OrderTimeline";
import { salesOrderDetail, type OrderDetailTab } from "./model";

export function SalesOrderDetailPage({ setRoute }: { setRoute: (route: RouteKey) => void }) {
  const [tab, setTab] = useState<OrderDetailTab>("summary");
  const order = salesOrderDetail;

  return (
    <>
      <OrderDetailHeader order={order} setRoute={setRoute} />
      <OrderTimeline order={order} />
      <OrderDetailTabs activeTab={tab} setActiveTab={setTab} />
      {tab === "summary" && <OrderSummaryTab order={order} setRoute={setRoute} />}
      {tab === "pays" && <OrderPaymentsTab order={order} />}
      {tab === "receipts" && <OrderReceiptsTab order={order} />}
      {tab === "fulfillment" && <OrderFulfillmentTab order={order} />}
      {tab === "subscription" && <OrderSubscriptionTab order={order} />}
      {tab === "audit" && <OrderAuditTab order={order} />}
    </>
  );
}
