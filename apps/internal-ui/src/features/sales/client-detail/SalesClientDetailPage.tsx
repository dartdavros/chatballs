import { useState } from "react";

import { EmptyState, LoadingState } from "../../../shared/ui";
import { type ClientDetailTab } from "./model";
import { SalesClientAuditTab } from "./SalesClientAuditTab";
import { SalesClientConsentTab } from "./SalesClientConsentTab";
import { SalesClientDialogsTab } from "./SalesClientDialogsTab";
import { SalesClientHeader } from "./SalesClientHeader";
import { SalesClientIdentitiesTab } from "./SalesClientIdentitiesTab";
import { SalesClientSalesTab } from "./SalesClientSalesTab";
import { SalesClientOverviewTab } from "./SalesClientOverviewTab";
import { SalesClientTabs } from "./SalesClientTabs";
import { useClientDetail } from "./useClientDetail";

export function SalesClientDetailPage({ contactId, openConversation }: { contactId: number | null; openConversation: (conversationId: number) => void }) {
  const [tab, setTab] = useState<ClientDetailTab>("overview");
  const { client, loading, error } = useClientDetail(contactId);

  if (loading) return <LoadingState />;
  if (error || !client) return <EmptyState title="Не удалось загрузить контакт" />;

  return (
    <>
      <SalesClientHeader client={client} openConversation={openConversation} />
      <SalesClientTabs activeTab={tab} setActiveTab={setTab} />
      {tab === "overview" && <SalesClientOverviewTab client={client} openConversation={openConversation} />}
      {tab === "dialogs" && <SalesClientDialogsTab dialogs={client.dialogs} openConversation={openConversation} />}
      {tab === "orders" && <SalesClientSalesTab contactId={contactId} />}
      {tab === "ids" && <SalesClientIdentitiesTab identities={client.identities} />}
      {tab === "consent" && <SalesClientConsentTab />}
      {tab === "audit" && <SalesClientAuditTab audit={client.audit} />}
    </>
  );
}
