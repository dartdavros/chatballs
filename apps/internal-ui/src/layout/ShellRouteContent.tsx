import { lazy, Suspense } from "react";

import { AiAgentsPage } from "../features/ai/AiAgentsPage";
import { AiAgentCreatePage } from "../features/ai/create/AiAgentCreatePage";
import { AiAgentDetailPage } from "../features/ai/detail/AiAgentDetailPage";
import { KnowledgeDetailPage } from "../features/ai/knowledge/KnowledgeDetailPage";
import { KnowledgeCreatePage } from "../features/ai/knowledge/KnowledgeCreatePage";
import { KnowledgePage } from "../features/ai/knowledge/KnowledgePage";
import { CommandCenter } from "../features/command/CommandCenter";
import { ChannelsPage } from "../features/channels/ChannelsPage";
import { ChannelDetailPage } from "../features/channels/ChannelDetailPage";
import { ChannelCreateWizard } from "../features/channels/ChannelCreateWizard";
import { IntegrationsPage } from "../features/integrations/IntegrationsPage";
import { DepartmentsPage } from "../features/departments/DepartmentsPage";
import { AccessProfilesPage, EmployeeDetailPage, EmployeesPage } from "../features/employees/EmployeesPage";
import { ProfilePage } from "../features/profile/ProfilePage";
import { SettingsPage } from "../features/settings/SettingsPage";
import { AdministrationPage } from "../features/administration/AdministrationPage";
import { SalesClientDetailPage } from "../features/sales/client-detail/SalesClientDetailPage";
import { SalesClientsPage } from "../features/sales/SalesClientsPage";
import { SalesDialogsPage } from "../features/sales/SalesDialogsPage";
import { SupportDialogsPage } from "../features/support/SupportDialogsPage";
import { SupportOverviewPage } from "../features/support/SupportOverviewPage";
import { LoadingState } from "../shared/ui";
import type { AppData, Employee, RouteKey, SessionUser } from "../types";
import { hasCapability } from "../auth/access";

const SupportPortalsPage = lazy(() => import("../features/support-portals/SupportPortalsPage").then(
  (module) => ({ default: module.SupportPortalsPage }),
));
const SupportPortalDetailPage = lazy(() => import("../features/support-portals/SupportPortalDetailPage").then(
  (module) => ({ default: module.SupportPortalDetailPage }),
));

export function ShellRouteContent({ route, data, currentEmployee, selectedProductCode, selectedAgentId, selectedKnowledgeId, selectedConversationId, selectedClientId, openClient, selectedChannelId, openChannel, selectedSupportPortalId, openSupportPortal, openConversation, openEmployee, openAgentCreate, openAgent, openKnowledge, onAgentLoaded, onChannelLoaded, reload, setRoute, user, onUserUpdated, onLogout }: { route: RouteKey; data: AppData; currentEmployee: Employee | null; selectedProductCode: string | null; selectedAgentId: number | null; selectedKnowledgeId: number | null; selectedConversationId: number | null; selectedClientId: number | null; openClient: (clientId: number) => void; selectedChannelId: number | null; openChannel: (channelId: number) => void; selectedSupportPortalId: number | null; openSupportPortal: (portalId: number) => void; openConversation: (conversationId: number) => void; openEmployee: (employee: Employee) => void; openAgentCreate: (productCode: string | null) => void; openAgent: (agentId: number) => void; openKnowledge: (knowledgeId: number) => void; onAgentLoaded: (name: string | null) => void; onChannelLoaded: (name: string | null) => void; reload: () => void; setRoute: (route: RouteKey) => void; user: SessionUser; onUserUpdated: (user: SessionUser) => void; onLogout: () => void }) {
  return (
    <>
      {route === "command" && <CommandCenter data={data} setRoute={setRoute} />}
      {route === "departments" && <DepartmentsPage data={data} setRoute={setRoute} />}
      {route === "employees" && <EmployeesPage departments={data.departments} employees={data.employees} reload={reload} openEmployee={openEmployee} setRoute={setRoute} user={user} />}
      {route === "accessProfiles" && <AccessProfilesPage setRoute={setRoute} />}
      {route === "employeeDetail" && currentEmployee && <EmployeeDetailPage departments={data.departments} employee={currentEmployee} reload={reload} setRoute={setRoute} user={user} />}
      {route === "employeeDetail" && !currentEmployee && <EmployeesPage departments={data.departments} employees={data.employees} reload={reload} openEmployee={openEmployee} setRoute={setRoute} user={user} />}
      {route === "profile" && <ProfilePage user={user} onUserUpdated={onUserUpdated} reload={reload} onLogout={onLogout} />}
      {route === "settings" && <SettingsPage user={user} onUserUpdated={onUserUpdated} reload={reload} />}
      {(route === "administrationOrganization"
        || route === "administrationSubscription"
        || route === "administrationAudit") && (
        <AdministrationPage
          route={route}
          user={user}
          onUserUpdated={onUserUpdated}
        />
      )}
      {route === "salesClients" && <SalesClientsPage openClient={openClient} />}
      {route === "salesClientDetail" && <SalesClientDetailPage contactId={selectedClientId} openConversation={openConversation} />}
      {route === "supportOverview" && <SupportOverviewPage />}
      {route === "supportDialogs" && <SupportDialogsPage initialConversationId={selectedConversationId} user={user} />}
      {route === "salesDialogs" && <SalesDialogsPage initialConversationId={selectedConversationId} user={user} />}
      {route === "aiAgents" && <AiAgentsPage agents={data.agents} reload={reload} openAgentCreate={openAgentCreate} openAgent={openAgent} />}
      {route === "aiAgentCreate" && <AiAgentCreatePage selectedProductCode={selectedProductCode} reload={reload} setRoute={setRoute} openAgent={openAgent} />}
      {route === "aiAgentDetail" && <AiAgentDetailPage agentId={selectedAgentId} openKnowledge={openKnowledge} openChannel={openChannel} onAgentLoaded={onAgentLoaded} setRoute={setRoute} />}
      {route === "aiKnowledge" && <KnowledgePage departments={data.departments} openAgent={openAgent} openKnowledge={openKnowledge} setRoute={setRoute} user={user} />}
      {route === "aiKnowledgeCreate" && <KnowledgeCreatePage departments={data.departments} openKnowledge={openKnowledge} setRoute={setRoute} />}
      {route === "aiKnowledgeDetail" && <KnowledgeDetailPage agents={data.agents} canManage={hasCapability(user, "ai.manage")} departments={data.departments} knowledgeId={selectedKnowledgeId} openAgent={openAgent} setRoute={setRoute} onLoaded={onAgentLoaded} />}
      {route === "channels" && <ChannelsPage user={user} departments={data.departments} openChannel={openChannel} openChannelCreate={() => setRoute("channelCreate")} openAgent={openAgent} />}
      {route === "channelDetail" && <ChannelDetailPage channelId={selectedChannelId} departments={data.departments} products={data.products} user={user} setRoute={setRoute} openAgent={openAgent} openChannels={() => setRoute("channels")} onChannelLoaded={onChannelLoaded} />}
      {route === "channelCreate" && <ChannelCreateWizard departments={data.departments} products={data.products} openChannel={openChannel} openChannels={() => setRoute("channels")} openAgentCreate={() => openAgentCreate(null)} openIntegrations={() => setRoute("integrations")} />}
      {route === "integrations" && <IntegrationsPage />}
      {route === "supportPortals" && <Suspense fallback={<LoadingState />}><SupportPortalsPage user={user} openPortal={openSupportPortal} /></Suspense>}
      {route === "supportPortalDetail" && <Suspense fallback={<LoadingState />}><SupportPortalDetailPage portalId={selectedSupportPortalId} products={data.products} user={user} openPortals={() => setRoute("supportPortals")} /></Suspense>}
    </>
  );
}
