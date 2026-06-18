import { useState } from "react";

import type { RouteKey } from "../../../types";
import { salesClientDetail, type ClientDetailTab } from "./model";
import { SalesClientAuditTab } from "./SalesClientAuditTab";
import { SalesClientConsentTab } from "./SalesClientConsentTab";
import { SalesClientDialogsTab } from "./SalesClientDialogsTab";
import { SalesClientHeader } from "./SalesClientHeader";
import { SalesClientIdentitiesTab } from "./SalesClientIdentitiesTab";
import { SalesClientOrdersTab } from "./SalesClientOrdersTab";
import { SalesClientOverviewTab } from "./SalesClientOverviewTab";
import { SalesClientTabs } from "./SalesClientTabs";

export function SalesClientDetailPage({ setRoute }: { setRoute: (route: RouteKey) => void }) {
  const [tab, setTab] = useState<ClientDetailTab>("overview");
  const client = salesClientDetail;

  return (
    <>
      <SalesClientHeader client={client} setRoute={setRoute} />
      <SalesClientTabs activeTab={tab} setActiveTab={setTab} />
      {tab === "overview" && <SalesClientOverviewTab client={client} setRoute={setRoute} />}
      {tab === "dialogs" && <SalesClientDialogsTab dialogs={client.dialogs} setRoute={setRoute} />}
      {tab === "orders" && <SalesClientOrdersTab orders={client.orders} />}
      {tab === "ids" && <SalesClientIdentitiesTab identities={client.identities} />}
      {tab === "consent" && <SalesClientConsentTab consent={client.consent} />}
      {tab === "audit" && <SalesClientAuditTab audit={client.audit} />}
    </>
  );
}
