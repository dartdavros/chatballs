import { lazy, Suspense } from "react";

import { AgentsPage } from "../features/agents/AgentsPage";
import { AgentDetailPage } from "../features/agents/AgentDetailPage";
import { KnowledgeDetailPage } from "../features/ai/knowledge/KnowledgeDetailPage";
import { KnowledgeCreatePage } from "../features/ai/knowledge/KnowledgeCreatePage";
import { KnowledgePage } from "../features/ai/knowledge/KnowledgePage";
import { EmployeeDetailPage, EmployeesPage } from "../features/employees/EmployeesPage";
import { ProfilePage } from "../features/profile/ProfilePage";
import { SettingsPage } from "../features/settings/SettingsPage";
import { AdministrationPage } from "../features/administration/AdministrationPage";
import { ChatPage } from "../features/chat/ChatPage";
import type { DialogScope } from "../features/conversations/ConversationWorkspace";
import type { ConversationCounters } from "../features/conversations/model";
import { SalesClientDetailPage } from "../features/sales/client-detail/SalesClientDetailPage";
import { SalesClientsPage } from "../features/sales/SalesClientsPage";
import { LoadingState } from "../shared/ui";
import type { AppData, Employee, RouteKey, SessionUser } from "../types";
import type { SettingsSectionKey } from "../features/settings/sections";
import { hasCapability } from "../auth/access";

const SupportPortalsPage = lazy(() => import("../features/support-portals/SupportPortalsPage").then(
  (module) => ({ default: module.SupportPortalsPage }),
));
const SupportPortalDetailPage = lazy(() => import("../features/support-portals/SupportPortalDetailPage").then(
  (module) => ({ default: module.SupportPortalDetailPage }),
));

export function ShellRouteContent({ settingsSection, openSettings, chatScope, setChatScope, chatCounters, chatScopeSwitcher, route, data, currentEmployee, selectedProductCode, selectedAgentId, selectedKnowledgeId, selectedConversationId, selectedClientId, openClient, selectedChannelId, openChannel, selectedSupportPortalId, openSupportPortal, openConversation, openEmployee, openAgentCreate, openAgent, openKnowledge, onAgentLoaded, onChannelLoaded, reload, setRoute, user, onUserUpdated, onLogout, onOpenSidebar }: { settingsSection: SettingsSectionKey | null; openSettings: (section: SettingsSectionKey | null) => void; chatScope: DialogScope; setChatScope: (scope: DialogScope) => void; chatCounters: ConversationCounters | null; chatScopeSwitcher: boolean; route: RouteKey; data: AppData; currentEmployee: Employee | null; selectedProductCode: string | null; selectedAgentId: number | null; selectedKnowledgeId: number | null; selectedConversationId: number | null; selectedClientId: number | null; openClient: (clientId: number) => void; selectedChannelId: number | null; openChannel: (channelId: number) => void; selectedSupportPortalId: number | null; openSupportPortal: (portalId: number) => void; openConversation: (conversationId: number) => void; openEmployee: (employee: Employee) => void; openAgentCreate: (productCode: string | null) => void; openAgent: (agentId: number) => void; openKnowledge: (knowledgeId: number) => void; onAgentLoaded: (name: string | null) => void; onChannelLoaded: (name: string | null) => void; reload: () => void; setRoute: (route: RouteKey) => void; user: SessionUser; onUserUpdated: (user: SessionUser) => void; onLogout: () => void; onOpenSidebar: () => void }) {
  return (
    <>
      {route === "employees" && <EmployeesPage groups={data.groups} employees={data.employees} reload={reload} openEmployee={openEmployee} setRoute={setRoute} user={user} />}
      {route === "employeeDetail" && currentEmployee && <EmployeeDetailPage groups={data.groups} employee={currentEmployee} employees={data.employees} reload={reload} setRoute={setRoute} />}
      {route === "employeeDetail" && !currentEmployee && <EmployeesPage groups={data.groups} employees={data.employees} reload={reload} openEmployee={openEmployee} setRoute={setRoute} user={user} />}
      {route === "profile" && <ProfilePage user={user} onUserUpdated={onUserUpdated} reload={reload} onLogout={onLogout} onBack={() => setRoute("chat")} />}
      {route === "settings" && <SettingsPage user={user} onUserUpdated={onUserUpdated} reload={reload} groups={data.groups} section={settingsSection} openSection={openSettings} setRoute={setRoute} />}
      {route === "administrationAudit" && (
        <AdministrationPage
          route={route}
          user={user}
          onUserUpdated={onUserUpdated}
        />
      )}
      {route === "salesClients" && <SalesClientsPage openClient={openClient} openIntegrations={() => openSettings("integrations")} />}
      {route === "salesClientDetail" && <SalesClientDetailPage contactId={selectedClientId} canEdit={hasCapability(user, "customers.manage")} canMerge={user.role === "OWNER"} openConversation={openConversation} openClient={openClient} openClients={() => setRoute("salesClients")} />}
      {route === "chat" && (
        <ChatPage
          initialConversationId={selectedConversationId}
          user={user}
          scope={chatScope}
          setScope={setChatScope}
          counters={chatCounters}
          showScopeSwitcher={chatScopeSwitcher}
          setRoute={setRoute}
          onLogout={onLogout}
          onOpenMenu={onOpenSidebar}
        />
      )}
      {route === "agents" && <AgentsPage agents={data.agents} groups={data.groups} reload={reload} openAgent={openAgent} />}
      {route === "agentDetail" && (
        <AgentDetailPage
          agentId={selectedAgentId}
          groups={data.groups}
          canManage={hasCapability(user, "ai.manage")}
          canManageConnections={hasCapability(user, "integrations.manage")}
          openAgents={() => setRoute("agents")}
          openKnowledge={openKnowledge}
          openIntegrations={() => openSettings("integrations")}
          openAiProvider={() => openSettings("ai")}
          setRoute={setRoute}
          onLoaded={onAgentLoaded}
        />
      )}
      {route === "aiKnowledge" && <KnowledgePage openAgent={openAgent} openKnowledge={openKnowledge} setRoute={setRoute} user={user} />}
      {route === "aiKnowledgeCreate" && <KnowledgeCreatePage openKnowledge={openKnowledge} setRoute={setRoute} />}
      {route === "aiKnowledgeDetail" && <KnowledgeDetailPage agents={data.agents} canManage={hasCapability(user, "ai.manage")} knowledgeId={selectedKnowledgeId} openAgent={openAgent} setRoute={setRoute} onLoaded={onAgentLoaded} />}
      {route === "supportPortals" && <Suspense fallback={<LoadingState />}><SupportPortalsPage user={user} openPortal={openSupportPortal} /></Suspense>}
      {route === "supportPortalDetail" && <Suspense fallback={<LoadingState />}><SupportPortalDetailPage portalId={selectedSupportPortalId} products={data.products} user={user} openPortals={() => setRoute("supportPortals")} /></Suspense>}
    </>
  );
}

// Кандидаты в «Ответственные»: id сотрудника в employee-API — это id пользователя.
