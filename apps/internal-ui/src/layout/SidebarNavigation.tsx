import type { RouteKey, SessionUser } from "../types";
import { Icon } from "../shared/icons";
import { SkillGlyph } from "../features/skills/SkillGlyph";
import { canViewReports, isManager } from "../auth/access";
import { useSupervision } from "../auth/useSupervision";
import type { TourTarget } from "../features/onboarding/steps";
import type { DialogScope } from "../features/conversations/ConversationWorkspace";
import type { ConversationCounters } from "../features/conversations/model";
import { ChatScopeTree } from "./ChatScopeTree";
import { SidebarHelpLink } from "./SidebarHelpLink";
import { NavigationIcon } from "./NavigationIcon";
import { t } from "../i18n";
import "./sidebar-navigation.css";

type SidebarLinkProps = {
  activeRoutes?: RouteKey[];
  badge?: string;
  icon: Parameters<typeof Icon>[0]["name"] | "stats" | "skill";
  label: string;
  route: RouteKey;
  routeKey: RouteKey;
  setRoute: (route: RouteKey) => void;
  // Имя цели для тура онбординга: по нему «Показать где» находит пункт на экране.
  target?: TourTarget;
};

function SidebarLink({ activeRoutes, badge, icon, label, route, routeKey, setRoute, target }: SidebarLinkProps) {
  const active = activeRoutes?.includes(route) ?? routeKey === route;
  return (
    <button
      className={`hub-nav-item ${active ? "is-active" : ""}`}
      type="button"
      aria-current={active ? "page" : undefined}
      data-onboarding-target={target}
      onClick={() => setRoute(routeKey)}
    >
      {icon === "stats" ? <NavigationIcon name="stats" /> : icon === "skill" ? <SkillGlyph /> : <Icon name={icon} strokeWidth={1.9} />}
      <span>{label}</span>
      {badge && <b className="hub-nav-badge">{badge}</b>}
    </button>
  );
}

export function SidebarNavigation({ route, user, setRoute, waitingCount, chatScope, setChatScope, chatCounters }: {
  route: RouteKey;
  user: SessionUser;
  setRoute: (route: RouteKey) => void;
  waitingCount: number;
  chatScope: DialogScope;
  setChatScope: (scope: DialogScope) => void;
  chatCounters: ConversationCounters | null;
}) {
  const manager = isManager(user);
  const supervision = useSupervision(user);
  return (
    manager ? (<>
        <nav className="hub-nav">
          <SidebarLink icon="message" label={t("common.chat")} badge={waitingCount > 0 ? String(waitingCount) : undefined} route={route} routeKey="chat" setRoute={setRoute} />
          <SidebarLink activeRoutes={["salesClients", "salesClientDetail"]} icon="user" label={t("common.contacts")} route={route} routeKey="salesClients" setRoute={setRoute} />
          <SidebarLink activeRoutes={["supportReports", "qualityAnalysis"]} icon="stats" label={t("reports.title")} route={route} routeKey="supportReports" setRoute={setRoute} />
          <div className="hub-nav-divider" aria-hidden="true" />
          <SidebarLink activeRoutes={["agents", "agentDetail"]} icon="robot" label={t("common.agents")} route={route} routeKey="agents" setRoute={setRoute} target="nav-agents" />
          <SidebarLink icon="skill" label={t("skills.title")} route={route} routeKey="skills" setRoute={setRoute} />
          <SidebarLink icon="workflow" label={t("scenarios.title")} route={route} routeKey="scenarios" setRoute={setRoute} />
          <SidebarLink icon="sparkles" label={t("navigation.ai_providers")} route={route} routeKey="aiProviders" setRoute={setRoute} target="nav-ai-providers" />
          <SidebarLink activeRoutes={["integrationServers", "externalServerSettings", "mcpServerCreate", "httpServerCreate"]} icon="server" label={t("navigation.tools")} route={route} routeKey="integrationServers" setRoute={setRoute} />
          <div className="hub-nav-divider" aria-hidden="true" />
          <SidebarLink activeRoutes={["knowledge", "knowledgeDetail", "knowledgeCreate", "knowledgeEdit", "knowledgeCategories", "knowledgeImport"]} icon="book" label={t("common.knowledge_base")} route={route} routeKey="knowledge" setRoute={setRoute} target="nav-knowledge" />
          <SidebarLink activeRoutes={["supportPortals", "supportPortalDetail", "supportPortalSettings"]} icon="globe" label={t("common.portals")} route={route} routeKey="supportPortals" setRoute={setRoute} />
          <div className="hub-nav-divider" aria-hidden="true" />
          <SidebarLink activeRoutes={["widgets", "webIntegrationSettings"]} icon="messageCircle" label={t("navigation.widgets")} route={route} routeKey="widgets" setRoute={setRoute} target="nav-widgets" />
          <SidebarLink icon="messagesSquare" label={t("navigation.messengers")} route={route} routeKey="messengers" setRoute={setRoute} target="nav-messengers" />
          <SidebarLink icon="mail" label={t("navigation.mail")} route={route} routeKey="emailIntegrations" setRoute={setRoute} />
          <SidebarLink activeRoutes={["serviceIntegrations", "serviceConnection"]} icon="plug" label={t("common.integrations")} route={route} routeKey="serviceIntegrations" setRoute={setRoute} />
          <div className="hub-nav-divider" aria-hidden="true" />
          <SidebarLink activeRoutes={["employees", "employeeDetail"]} icon="team" label={t("common.operators")} route={route} routeKey="employees" setRoute={setRoute} target="nav-employees" />
          <SidebarLink activeRoutes={["ruleJournal", "settings", "administrationAudit"]} icon="settings" label={t("common.settings")} route={route} routeKey="settings" setRoute={setRoute} />
        </nav>
        <SidebarHelpFooter />
      </>) : route === "profile" || route === "replyTemplates" ? (
        /* Кадр P2: на «Профиле» у сотрудника сайдбар без навигации — фильтровать
           нечего, дерево диалогов относится только к чату. Так же устроена
           страница «Шаблоны ответов» из меню пользователя. */
        null
      ) : (<>
        <ChatScopeTree
          supervision={supervision}
          footer={canViewReports(supervision) ? <>
            <div className="hub-nav-divider" aria-hidden="true" />
            <SidebarLink activeRoutes={["supportReports", "qualityAnalysis"]} icon="stats" label={t("reports.title")} route={route} routeKey="supportReports" setRoute={setRoute} />
          </> : undefined}
          route={route}
          scope={chatScope}
          counters={chatCounters}
          setScope={(scope) => {
            setChatScope(scope);
            setRoute("chat");
          }}
        />
        <SidebarHelpFooter />
      </>)
  );
}

function SidebarHelpFooter() {
  return <div className="hub-sidebar-help"><div className="hub-nav-divider" aria-hidden="true" /><SidebarHelpLink /></div>;
}
