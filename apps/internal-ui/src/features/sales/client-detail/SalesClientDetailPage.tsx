import { useState } from "react";

import { EmptyState, LoadingState } from "../../../shared/ui";
import type { RouteKey } from "../../../types";
import { type ClientDetailTab } from "./model";
import { SalesClientAuditTab } from "./SalesClientAuditTab";
import { SalesClientConsentTab } from "./SalesClientConsentTab";
import { SalesClientDialogsTab } from "./SalesClientDialogsTab";
import { SalesClientHeader } from "./SalesClientHeader";
import { SalesClientIdentitiesTab } from "./SalesClientIdentitiesTab";
import { SalesClientOrdersTab } from "./SalesClientOrdersTab";
import { SalesClientOverviewTab } from "./SalesClientOverviewTab";
import { SalesClientTabs } from "./SalesClientTabs";
import { useClientDetail } from "./useClientDetail";

export function SalesClientDetailPage({ contactId, setRoute }: { contactId: number | null; setRoute: (route: RouteKey) => void }) {
  const [tab, setTab] = useState<ClientDetailTab>("overview");
  const { client, loading, error } = useClientDetail(contactId);

  if (loading) return <LoadingState />;
  if (error || !client) return <EmptyState title="Не удалось загрузить клиента" />;

  return (
    <>
      <SalesClientHeader client={client} setRoute={setRoute} />
      <SalesClientTabs activeTab={tab} setActiveTab={setTab} />
      {tab === "overview" && <SalesClientOverviewTab client={client} setRoute={setRoute} />}
      {tab === "dialogs" && <SalesClientDialogsTab dialogs={client.dialogs} setRoute={setRoute} />}
      {tab === "orders" && <SalesClientOrdersTab orders={client.orders} />}
      {tab === "ids" && <SalesClientIdentitiesTab identities={client.identities} />}
      {tab === "consent" && <SalesClientConsentTab />}
      {tab === "audit" && <SalesClientAuditTab audit={client.audit} />}
    </>
  );
}
