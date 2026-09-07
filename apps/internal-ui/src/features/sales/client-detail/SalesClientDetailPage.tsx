import { useState } from "react";

import { EmptyState, LoadingState } from "../../../shared/ui";
import { BackLink, UnderlineTabs } from "../../../shared/ui-controls";
import { clientDetailTabsOf, type ClientDetailTab } from "./model";
import { SalesClientAuditTab } from "./SalesClientAuditTab";
import { SalesClientDialogsTab } from "./SalesClientDialogsTab";
import { SalesClientHeader } from "./SalesClientHeader";
import { SalesClientIdentitiesTab } from "./SalesClientIdentitiesTab";
import { SalesClientOverviewTab } from "./SalesClientOverviewTab";
import { useClientDetail } from "./useClientDetail";

// Карточка контакта (кадры K3–K5): возврат к списку, шапка, вкладки
// Обзор · Диалоги · Идентификаторы · Аудит.
export function SalesClientDetailPage({ contactId, canEdit = false, canMerge = false, openConversation, openClient, openClients }: { contactId: number | null; canEdit?: boolean; canMerge?: boolean; openConversation: (conversationId: number) => void; openClient: (id: number) => void; openClients: () => void }) {
  const [tab, setTab] = useState<ClientDetailTab>("overview");
  const { client, loading, error, save, merge } = useClientDetail(contactId);

  if (loading) return <div className="sales-client-page"><LoadingState /></div>;
  if (error || !client) return <div className="sales-client-page"><EmptyState title="Не удалось загрузить контакт" /></div>;

  return (
    <div className="sales-client-page">
      <BackLink label="Контакты" onClick={openClients} />
      <SalesClientHeader client={client} canEdit={canEdit} openConversation={openConversation} onSave={save} />
      <UnderlineTabs className="sales-client-detail-tabs" items={clientDetailTabsOf(client)} value={tab} onChange={setTab} />
      {tab === "overview" && <SalesClientOverviewTab client={client} openConversation={openConversation} />}
      {tab === "dialogs" && <SalesClientDialogsTab dialogs={client.dialogs} openConversation={openConversation} />}
      {tab === "ids" && <SalesClientIdentitiesTab client={client} canMerge={canMerge} openClient={openClient} onMerge={merge} />}
      {tab === "audit" && <SalesClientAuditTab audit={client.audit} />}
    </div>
  );
}
