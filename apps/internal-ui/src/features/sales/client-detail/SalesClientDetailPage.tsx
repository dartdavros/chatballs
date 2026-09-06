import { useState } from "react";

import { EmptyState, LoadingState } from "../../../shared/ui";
import { type ClientDetailTab } from "./model";
import { SalesClientAuditTab } from "./SalesClientAuditTab";
import { SalesClientConsentTab } from "./SalesClientConsentTab";
import { SalesClientDialogsTab } from "./SalesClientDialogsTab";
import { SalesClientHeader } from "./SalesClientHeader";
import { SalesClientIdentitiesTab } from "./SalesClientIdentitiesTab";
import { SalesClientOverviewTab } from "./SalesClientOverviewTab";
import { SalesClientTabs } from "./SalesClientTabs";
import { useClientDetail } from "./useClientDetail";

export function SalesClientDetailPage({ contactId, canEdit = false, openConversation }: { contactId: number | null; canEdit?: boolean; openConversation: (conversationId: number) => void }) {
  const [tab, setTab] = useState<ClientDetailTab>("overview");
  const { client, loading, error, save } = useClientDetail(contactId);

  if (loading) return <LoadingState />;
  if (error || !client) return <EmptyState title="Не удалось загрузить контакт" />;

  return (
    <>
      <SalesClientHeader client={client} canEdit={canEdit} openConversation={openConversation} onSave={save} />
      <SalesClientTabs activeTab={tab} setActiveTab={setTab} />
      {tab === "overview" && <SalesClientOverviewTab client={client} openConversation={openConversation} />}
      {tab === "dialogs" && <SalesClientDialogsTab dialogs={client.dialogs} openConversation={openConversation} />}
      {tab === "ids" && <SalesClientIdentitiesTab identities={client.identities} />}
      {tab === "consent" && <SalesClientConsentTab />}
      {tab === "audit" && <SalesClientAuditTab audit={client.audit} />}
    </>
  );
}
