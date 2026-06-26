import { commandCenterModel } from "../features/command/CommandCenter";
import { routes } from "../routes";
import type { Employee, Product, RouteKey, SessionUser } from "../types";
import { Icon } from "../shared/icons";

export function TopBar({ route, user, currentEmployee, currentProduct, currentAgentName, setRoute }: { route: RouteKey; user: SessionUser; currentEmployee?: Employee | null; currentProduct?: Product | null; currentAgentName?: string | null; setRoute: (route: RouteKey) => void }) {
  const st = commandCenterModel("today").st;
  const isCommand = route === "command";
  const isAiDetail = route === "aiAgentDetail" || route === "aiRelease";
  const isAi = route.startsWith("ai") && !isAiDetail && route !== "aiAgentCreate";
  const [releaseAgentName, releaseName] = route === "aiRelease" && currentAgentName?.includes("|") ? currentAgentName.split("|") : [currentAgentName, null];
  const isSalesWorkspace = route === "salesOverview" || route === "salesClientDetail" || route === "salesClients" || route === "salesDialogs" || route === "salesOrderDetail" || route === "salesOrders";
  return (
    <header className="hub-topbar">
      <div className="breadcrumbs">
        <button type="button" onClick={() => setRoute("command")}>{user.organizationName}</button>
        <i>/</i>
        {route === "employeeDetail" && <><button type="button" onClick={() => setRoute("employees")}>Сотрудники</button><i>/</i><strong>{currentEmployee?.fullName || currentEmployee?.email || routes[route]}</strong></>}
        {route === "productDetail" && <><button type="button" onClick={() => setRoute("products")}>Продукты</button><i>/</i><strong>{currentProduct?.name || routes[route]}</strong></>}
        {isSalesWorkspace && route !== "salesClientDetail" && route !== "salesOrderDetail" && <><button type="button" onClick={() => setRoute("salesOverview")}>Продажи</button><i>/</i><strong>{routes[route]}</strong></>}
        {route === "salesClientDetail" && <><button type="button" onClick={() => setRoute("salesOverview")}>Продажи</button><i>/</i><button type="button" onClick={() => setRoute("salesClients")}>Клиенты</button><i>/</i><strong>{routes[route]}</strong></>}
        {route === "salesOrderDetail" && <><button type="button" onClick={() => setRoute("salesOverview")}>Продажи</button><i>/</i><button type="button" onClick={() => setRoute("salesOrders")}>Продажи</button><i>/</i><strong className="topbar-mono">{routes[route]}</strong></>}
        {isAi && <><button type="button" onClick={() => setRoute("aiAgents")}>AI</button><i>/</i><strong>{routes[route]}</strong></>}
        {route === "aiAgentCreate" && <><button type="button" onClick={() => setRoute("aiAgents")}>AI</button><i>/</i><button type="button" onClick={() => setRoute("aiAgents")}>AI-агенты</button><i>/</i><strong>{routes[route]}</strong></>}
        {route === "aiAgentDetail" && <><button type="button" onClick={() => setRoute("aiAgents")}>AI</button><i>/</i><button type="button" onClick={() => setRoute("aiAgents")}>AI-агенты</button><i>/</i><strong>{currentAgentName || routes[route]}</strong></>}
        {route === "aiRelease" && <><button type="button" onClick={() => setRoute("aiAgents")}>AI</button><i>/</i><button type="button" onClick={() => setRoute("aiAgents")}>{releaseAgentName || "AI-агенты"}</button><i>/</i><strong className="topbar-mono">{releaseName || routes[route]}</strong></>}
        {route !== "employeeDetail" && route !== "productDetail" && route !== "aiAgentCreate" && !isSalesWorkspace && !isAi && !isAiDetail && <strong>{routes[route]}</strong>}
      </div>
      <div className="topbar-actions">
        {isCommand && <span className="topbar-status" style={{ background: st.bg, borderColor: st.border, color: st.color }}><span style={{ background: st.dot }} />{st.label}</span>}
        <button className="icon-button" aria-label="Уведомления"><Icon name="bell" size={18} /><b className={isCommand ? "" : "is-dot"}>{isCommand ? "2" : ""}</b></button>
      </div>
    </header>
  );
}
