import type { RouteKey, SessionUser } from "../types";
import { Icon } from "../shared/icons";
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
  icon: Parameters<typeof Icon>[0]["name"] | "stats";
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
      data-onboarding-target={target}
      onClick={() => setRoute(routeKey)}
    >
      {icon === "stats" ? <NavigationIcon name="stats" /> : <Icon name={icon} strokeWidth={1.9} />}
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
    manager ? (
        <nav className="hub-nav">
          <SidebarLink icon="message" label={t("common.chat")} badge={waitingCount > 0 ? String(waitingCount) : undefined} route={route} routeKey="chat" setRoute={setRoute} />
          <SidebarLink activeRoutes={["salesClients", "salesClientDetail"]} icon="user" label={t("common.contacts")} route={route} routeKey="salesClients" setRoute={setRoute} />
          <SidebarLink activeRoutes={["agents", "agentDetail", "skills"]} icon="robot" label={t("common.agents")} route={route} routeKey="agents" setRoute={setRoute} target="nav-agents" />
          <SidebarLink activeRoutes={["employees", "employeeDetail"]} icon="team" label={t("common.operators")} route={route} routeKey="employees" setRoute={setRoute} target="nav-employees" />
          <SidebarLink activeRoutes={["supportPortals", "supportPortalDetail", "supportPortalSettings"]} icon="globe" label={t("common.portals")} route={route} routeKey="supportPortals" setRoute={setRoute} />
          <SidebarLink activeRoutes={["knowledge", "knowledgeDetail", "knowledgeCreate", "knowledgeEdit", "knowledgeCategories", "knowledgeImport"]} icon="book" label={t("common.knowledge_base")} route={route} routeKey="knowledge" setRoute={setRoute} target="nav-knowledge" />
          <div className="hub-nav-divider" />
          <SidebarLink activeRoutes={["supportReports", "qualityAnalysis"]} icon="stats" label={t("reports.title")} route={route} routeKey="supportReports" setRoute={setRoute} />
          <SidebarLink activeRoutes={["ruleJournal", "settings", "webIntegrationSettings", "mcpServerCreate", "httpServerCreate", "integrationServers", "serviceIntegrations", "serviceConnection", "administrationAudit"]} icon="settings" label={t("common.settings")} route={route} routeKey="settings" setRoute={setRoute} />
          <SidebarHelpLink />
        </nav>
      ) : route === "profile" || route === "replyTemplates" ? (
        /* Кадр P2: на «Профиле» у сотрудника сайдбар без навигации — фильтровать
           нечего, дерево диалогов относится только к чату. Так же устроена
           страница «Шаблоны ответов» из меню пользователя. */
        null
      ) : (
        <ChatScopeTree
          supervision={supervision}
          footer={<>
            <div className="hub-nav-divider" />
            {canViewReports(supervision) &&
            <SidebarLink activeRoutes={["supportReports", "qualityAnalysis"]} icon="stats" label={t("reports.title")} route={route} routeKey="supportReports" setRoute={setRoute} />
            }
            <SidebarHelpLink />
          </>}
          route={route}
          scope={chatScope}
          counters={chatCounters}
          setScope={(scope) => {
            setChatScope(scope);
            setRoute("chat");
          }}
        />
      )
  );
}
