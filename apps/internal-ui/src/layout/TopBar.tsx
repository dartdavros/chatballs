import { routes } from "../routes";
import type { Employee, RouteKey, SessionUser } from "../types";
import { Icon } from "../shared/icons";

export function TopBar({ route, user, currentEmployee, currentAgentName, currentChannelName, setRoute, unreadCount = 0, onOpenNotifications }: { route: RouteKey; user: SessionUser; currentEmployee?: Employee | null; currentAgentName?: string | null; currentChannelName?: string | null; setRoute: (route: RouteKey) => void; unreadCount?: number; onOpenNotifications?: () => void }) {
  const isCommand = route === "command";
  const isAiDetail = route === "aiKnowledgeCreate" || route === "aiKnowledgeDetail";
  const isAi = route.startsWith("ai") && !isAiDetail;
  const isSupportWorkspace = route === "supportOverview" || route === "supportPortals" || route === "supportPortalDetail";
  return (
    <header className="hub-topbar">
      <div className="breadcrumbs">
        <button type="button" onClick={() => setRoute("command")}>{user.organizationName}</button>
        <i>/</i>
        {route === "employeeDetail" && <><button type="button" onClick={() => setRoute("employees")}>Сотрудники</button><i>/</i><strong>{currentEmployee?.fullName || currentEmployee?.email || routes[route]}</strong></>}
        {route === "agentDetail" && <><button type="button" onClick={() => setRoute("agents")}>Агенты</button><i>/</i><strong>{currentAgentName || routes[route]}</strong></>}
        {route === "salesClientDetail" && <><button type="button" onClick={() => setRoute("salesClients")}>Контакты</button><i>/</i><strong>{routes[route]}</strong></>}
        {isSupportWorkspace && route !== "supportPortalDetail" && <><button type="button" onClick={() => setRoute("supportOverview")}>Поддержка</button><i>/</i><strong>{routes[route]}</strong></>}
        {route === "supportPortalDetail" && <><button type="button" onClick={() => setRoute("supportOverview")}>Поддержка</button><i>/</i><button type="button" onClick={() => setRoute("supportPortals")}>Порталы</button><i>/</i><strong>{routes[route]}</strong></>}
        {isAi && <><button type="button" onClick={() => setRoute("aiKnowledge")}>AI</button><i>/</i><strong>{routes[route]}</strong></>}
        {route === "aiKnowledgeDetail" && <><button type="button" onClick={() => setRoute("aiKnowledge")}>AI</button><i>/</i><button type="button" onClick={() => setRoute("aiKnowledge")}>Знания</button><i>/</i><strong>{currentAgentName || routes[route]}</strong></>}
        {route === "aiKnowledgeCreate" && <><button type="button" onClick={() => setRoute("aiKnowledge")}>AI</button><i>/</i><button type="button" onClick={() => setRoute("aiKnowledge")}>Знания</button><i>/</i><strong>{routes[route]}</strong></>}
        {route !== "employeeDetail" && route !== "agentDetail" && route !== "supportPortalDetail" && route !== "salesClientDetail" && !isSupportWorkspace && !isAi && !isAiDetail && <strong>{routes[route]}</strong>}
      </div>
      <div className="topbar-actions">
        <button className="icon-button" aria-label="Уведомления" onClick={onOpenNotifications}><Icon name="bell" size={18} />{unreadCount > 0 && <b>{unreadCount > 99 ? "99+" : unreadCount}</b>}</button>
      </div>
    </header>
  );
}
