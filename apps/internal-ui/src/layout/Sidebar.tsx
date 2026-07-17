import type { RouteKey, SessionUser } from "../types";
import { Icon, LogoIcon } from "../shared/icons";
import { canAccess } from "../auth/access";
import { SidebarUserMenu } from "./SidebarUserMenu";

export function Sidebar({ route, user, setRoute, onLogout }: { route: RouteKey; user: SessionUser; setRoute: (route: RouteKey) => void; onLogout: () => void }) {
  const nav = [
    { key: "command" as const, label: "Обзор", icon: "grid" as const },
    { label: "КОМПАНИЯ", group: true },
    { key: "departments" as const, label: "Отделы", icon: "building" as const },
    { key: "employees" as const, label: "Сотрудники", icon: "team" as const },
    { key: "products" as const, label: "Продукты", icon: "box" as const },
    { label: "ПЛАТФОРМА", group: true },
    { key: "aiAgents" as const, label: "AI", icon: "robot" as const },
    { key: "integrations" as const, label: "Интеграции", icon: "plug" as const },
    { divider: true },
    { label: "Настройки", icon: "settings" as const, disabled: true },
  ];
  return (
    <aside className="hub-sidebar">
      <button className="hub-brand" type="button" onClick={() => setRoute("command")}>
        <div className="hub-brand-mark"><LogoIcon /></div>
        <div><strong>CustoCRM</strong><span>Управление компанией</span></div>
      </button>
      <nav className="hub-nav">
        {nav.map((item, index) => {
          if ("group" in item) return <div className="hub-nav-group" key={item.label}>{item.label}</div>;
          if ("divider" in item) return <div className="hub-nav-divider" key={index} />;
          const nextRoute = "key" in item ? item.key : null;
          if (nextRoute && !canAccess(user, nextRoute)) return null;
          const active = nextRoute === route || (nextRoute === "employees" && (route === "employeeDetail" || route === "accessProfiles")) || (nextRoute === "products" && route === "productDetail") || (nextRoute === "aiAgents" && route.startsWith("ai"));
          return (
            <button className={`hub-nav-item ${active ? "is-active" : ""}`} disabled={item.disabled} key={item.label} onClick={() => nextRoute && setRoute(nextRoute)}>
              {active && <span className="active-bar" />}
              <Icon name={item.icon} />
              {item.label}
            </button>
          );
        })}
      </nav>
      <SidebarUserMenu user={user} route={route} setRoute={setRoute} onLogout={onLogout} />
    </aside>
  );
}
