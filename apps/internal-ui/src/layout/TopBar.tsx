import { commandCenterModel } from "../features/command/CommandCenter";
import { routes } from "../routes";
import type { Employee, RouteKey, SessionUser } from "../types";
import { Icon } from "../shared/icons";

export function TopBar({ route, user, currentEmployee, setRoute }: { route: RouteKey; user: SessionUser; currentEmployee?: Employee | null; setRoute: (route: RouteKey) => void }) {
  const st = commandCenterModel("today").st;
  const isCommand = route === "command";
  const isSalesWorkspace = route === "salesOverview" || route === "salesClientDetail" || route === "salesClients" || route === "salesDialogs";
  return (
    <header className="hub-topbar">
      <div className="breadcrumbs">
        <button type="button" onClick={() => setRoute("command")}>{user.organizationName}</button>
        <i>/</i>
        {route === "employeeDetail" && <><button type="button" onClick={() => setRoute("employees")}>Сотрудники</button><i>/</i><strong>{currentEmployee?.fullName || currentEmployee?.email || routes[route]}</strong></>}
        {isSalesWorkspace && route !== "salesClientDetail" && <><button type="button" onClick={() => setRoute("salesOverview")}>Продажи</button><i>/</i><strong>{routes[route]}</strong></>}
        {route === "salesClientDetail" && <><button type="button" onClick={() => setRoute("salesOverview")}>Продажи</button><i>/</i><button type="button" onClick={() => setRoute("salesClients")}>Клиенты</button><i>/</i><strong>{routes[route]}</strong></>}
        {route !== "employeeDetail" && !isSalesWorkspace && <strong>{routes[route]}</strong>}
      </div>
      <div className="topbar-actions">
        {isCommand && <span className="topbar-status" style={{ background: st.bg, borderColor: st.border, color: st.color }}><span style={{ background: st.dot }} />{st.label}</span>}
        <button className="icon-button" aria-label="Уведомления"><Icon name="bell" size={18} /><b className={isCommand ? "" : "is-dot"}>{isCommand ? "2" : ""}</b></button>
      </div>
    </header>
  );
}
