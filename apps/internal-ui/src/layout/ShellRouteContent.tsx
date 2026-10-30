import { SkillsWorkspace } from "../features/skills/SkillsWorkspace";
import { lazy, Suspense } from "react";

import { AgentsPage } from "../features/agents/AgentsPage";
import { AgentDetailPage } from "../features/agents/AgentDetailPage";
import { EmployeeDetailPage, EmployeesPage } from "../features/employees/EmployeesPage";
import { ProfilePage } from "../features/profile/ProfilePage";
import { SettingsPage } from "../features/settings/SettingsPage";
import { RuleJournalPage } from "../features/handling-rules/RuleJournalPage";
import { ReplyTemplateLibrary } from "../features/reply-templates/ReplyTemplateLibrary";
import { IntegrationSettingsPage } from "../features/integrations/IntegrationSettingsPage";
import { AuditPage } from "../features/administration/AuditPage";
import { OrganizationCreatePage } from "../features/organizations/OrganizationCreatePage";
import { ChatPage } from "../features/chat/ChatPage";
import type { DialogScope } from "../features/conversations/ConversationWorkspace";
import type { ConversationCounters } from "../features/conversations/model";
import { SalesClientDetailPage } from "../features/sales/client-detail/SalesClientDetailPage";
import { SalesClientsPage } from "../features/sales/SalesClientsPage";
import { LoadingState } from "../shared/ui";
import type { AppData, AuthenticatedUser, Employee, RouteKey, SessionUser } from "../types";
import type { SettingsSectionKey } from "../features/settings/sections";
import type { PortalSettingsSectionKey } from "../features/support-portals/sections";
import { hasCapability, isManager } from "../auth/access";
import { integrationsView, isIntegrationsRoute } from "../features/integrations/tabs";
import { QualityAnalysisPage } from "../features/quality/QualityAnalysisPage";

// Раздел «База знаний» грузится отдельным чанком: у сотрудника его нет,
// а в редакторе тянется Markdown-предпросмотр (кадры KB1–KB9).
const KnowledgeLibraryPage = lazy(() => import("../features/ai/knowledge/KnowledgeLibraryPage").then(
  (module) => ({ default: module.KnowledgeLibraryPage }),
));
const KnowledgeCardPage = lazy(() => import("../features/ai/knowledge/KnowledgeCardPage").then(
  (module) => ({ default: module.KnowledgeCardPage }),
));
const KnowledgeEditorPage = lazy(() => import("../features/ai/knowledge/KnowledgeEditorPage").then(
  (module) => ({ default: module.KnowledgeEditorPage }),
));
const KnowledgeCategoriesPage = lazy(() => import("../features/ai/knowledge/KnowledgeCategoriesPage").then(
  (module) => ({ default: module.KnowledgeCategoriesPage }),
));
const KnowledgeImportPage = lazy(() => import("../features/ai/knowledge/KnowledgeImportPage").then(
  (module) => ({ default: module.KnowledgeImportPage }),
));

const SupportPortalsPage = lazy(() => import("../features/support-portals/SupportPortalsPage").then(
  (module) => ({ default: module.SupportPortalsPage }),
));
const SupportReportsPage = lazy(() => import("../features/support-reports/SupportReportsPage").then(
  (module) => ({ default: module.SupportReportsPage }),
));
const SupportPortalDetailPage = lazy(() => import("../features/support-portals/SupportPortalDetailPage").then(
  (module) => ({ default: module.SupportPortalDetailPage }),
));

export function ShellRouteContent({ settingsSection, openSettings, chatScope, setChatScope, chatCounters, chatScopeSwitcher, route, data, selectedEmployeeId, selectedAgentId, selectedKnowledgeId, selectedConversationId, selectedClientId, openClient, selectedChannelId, openChannel, selectedIntegrationId, openWebIntegration, openServiceConnection, selectedSupportPortalId, portalSettingsSection, openSupportPortal, openPortalSettings, openConversation, openEmployee, openAgent, openKnowledge, openKnowledgeEditor, onAgentLoaded, onChannelLoaded, reload, setRoute, user, onUserUpdated, onLogout, onOpenSidebar, onOrganizationCreated }: { settingsSection: SettingsSectionKey | null; openSettings: (section: SettingsSectionKey | null) => void; chatScope: DialogScope; setChatScope: (scope: DialogScope) => void; chatCounters: ConversationCounters | null; chatScopeSwitcher: boolean; route: RouteKey; data: AppData; selectedEmployeeId: number | null; selectedAgentId: number | null; selectedKnowledgeId: number | null; selectedConversationId: number | null; selectedClientId: number | null; openClient: (clientId: number) => void; selectedChannelId: number | null; openChannel: (channelId: number) => void; selectedIntegrationId: number | null; openWebIntegration: (id: number) => void; openServiceConnection: (id: number) => void; selectedSupportPortalId: number | null; portalSettingsSection: PortalSettingsSectionKey | null; openSupportPortal: (portalId: number) => void; openPortalSettings: (portalId: number, section?: PortalSettingsSectionKey) => void; openConversation: (conversationId: number) => void; openEmployee: (employee: Employee) => void; openAgent: (agentId: number) => void; openKnowledge: (knowledgeId: number) => void; openKnowledgeEditor: (knowledgeId: number | null) => void; onAgentLoaded: (name: string | null) => void; onChannelLoaded: (name: string | null) => void; reload: () => void; setRoute: (route: RouteKey) => void; user: SessionUser; onUserUpdated: (user: SessionUser) => void; onLogout: () => void; onOpenSidebar: () => void; onOrganizationCreated: (identity: AuthenticatedUser, organizationPublicId: string) => void }) {
  return (
    <>
      {route === "employees" && <EmployeesPage groups={data.groups} openEmployee={openEmployee} setRoute={setRoute} user={user} />}
      {route === "employeeDetail" && selectedEmployeeId != null && <EmployeeDetailPage groups={data.groups} employeeId={selectedEmployeeId} setRoute={setRoute} />}
      {route === "employeeDetail" && selectedEmployeeId == null && <EmployeesPage groups={data.groups} openEmployee={openEmployee} setRoute={setRoute} user={user} />}
      {route === "profile" && <ProfilePage user={user} onUserUpdated={onUserUpdated} reload={reload} onLogout={onLogout} onBack={() => setRoute("chat")} />}
      {route === "replyTemplates" && <ReplyTemplateLibrary employee onBack={() => setRoute("chat")} />}
      {(route === "settings" || isIntegrationsRoute(route) || route === "ruleJournal" && isManager(user)) && <SettingsPage user={user} onUserUpdated={onUserUpdated} reload={reload} groups={data.groups} section={settingsSection} openSection={openSettings} openWebIntegration={openWebIntegration} openServiceConnection={openServiceConnection} integrationsView={integrationsView(route, selectedIntegrationId)} setRoute={setRoute} journal={route === "ruleJournal"} openConversation={openConversation} />}
      {route === "ruleJournal" && !isManager(user) && <RuleJournalPage openConversation={openConversation} />}
      {route === "webIntegrationSettings" && selectedIntegrationId !== null && <IntegrationSettingsPage integrationId={selectedIntegrationId} onCreated={openWebIntegration} onOpenSettings={() => openSettings(null)} onBack={() => openSettings("integrations")} />}
      {(route === "mcpServerCreate" || route === "httpServerCreate") && <IntegrationSettingsPage key={route} createKind={route === "mcpServerCreate" ? "mcp" : "http"} onCreated={openWebIntegration} onOpenSettings={() => openSettings(null)} onBack={() => openSettings("integrations")} />}
      {route === "administrationAudit" && <AuditPage />}
      {route === "supportReports" && <SupportReportsPage onDialogs={() => setRoute("chat")} />}
      {route === "qualityAnalysis" && selectedConversationId !== null && <QualityAnalysisPage key={selectedConversationId} id={selectedConversationId} user={user} back={() => openConversation(selectedConversationId)} />}
      {route === "organizationCreate" && <OrganizationCreatePage user={user} onCreated={onOrganizationCreated} onBack={() => setRoute("chat")} />}
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
      {route === "skills" && <SkillsWorkspace agents={data.agents} openAgent={openAgent} back={() => setRoute("agents")} />}
      {route === "agents" && <AgentsPage groups={data.groups} openAgent={openAgent} openSkills={() => setRoute("skills")} />}
      {route === "agentDetail" && (
        <AgentDetailPage
          agentId={selectedAgentId}
          groups={data.groups}
          canManage={hasCapability(user, "ai.manage")}
          canManageConnections={hasCapability(user, "integrations.manage")}
          openAgents={() => setRoute("agents")}
          openKnowledge={openKnowledge}
          openIntegrations={() => openSettings("integrations")}
          openServer={openWebIntegration}
          openAiProvider={() => openSettings("ai")}
          setRoute={setRoute}
          onLoaded={onAgentLoaded}
        />
      )}
      {route === "knowledge" && (
        <Suspense fallback={<LoadingState />}>
          <KnowledgeLibraryPage agents={data.agents} openKnowledge={openKnowledge} openKnowledgeEditor={openKnowledgeEditor} setRoute={setRoute} user={user} />
        </Suspense>
      )}
      {route === "knowledgeDetail" && (
        <Suspense fallback={<LoadingState />}>
          <KnowledgeCardPage agents={data.agents} canManage={hasCapability(user, "ai.manage")} knowledgeId={selectedKnowledgeId} openKnowledgeEditor={openKnowledgeEditor} reloadAgents={reload} setRoute={setRoute} />
        </Suspense>
      )}
      {(route === "knowledgeCreate" || route === "knowledgeEdit") && (
        <Suspense fallback={<LoadingState />}>
          <KnowledgeEditorPage agents={data.agents} canManage={hasCapability(user, "ai.manage")} knowledgeId={route === "knowledgeEdit" ? selectedKnowledgeId : null} openKnowledge={openKnowledge} reloadAgents={reload} setRoute={setRoute} />
        </Suspense>
      )}
      {route === "knowledgeCategories" && (
        <Suspense fallback={<LoadingState />}>
          <KnowledgeCategoriesPage canManage={hasCapability(user, "ai.manage")} setRoute={setRoute} />
        </Suspense>
      )}
      {route === "knowledgeImport" && (
        <Suspense fallback={<LoadingState />}>
          <KnowledgeImportPage canManage={hasCapability(user, "ai.manage")} setRoute={setRoute} />
        </Suspense>
      )}
      {route === "supportPortals" && <Suspense fallback={<LoadingState />}><SupportPortalsPage user={user} openPortal={openSupportPortal} openPortalSettings={openPortalSettings} /></Suspense>}
      {(route === "supportPortalDetail" || route === "supportPortalSettings") && (
        <Suspense fallback={<LoadingState />}>
          <SupportPortalDetailPage
            portalId={selectedSupportPortalId}
            section={route === "supportPortalSettings" ? portalSettingsSection : null}
            user={user}
            openPortals={() => setRoute("supportPortals")}
            openPortalContent={openSupportPortal}
            openPortalSettings={openPortalSettings}
          />
        </Suspense>
      )}
    </>
  );
}

// Кандидаты в «Ответственные»: id сотрудника в employee-API — это id пользователя.
