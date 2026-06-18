import type { RouteKey, SessionUser } from "../types";
import { Icon, PulseIcon } from "../shared/icons";
import { Avatar } from "../shared/ui";

export function Sidebar({ route, user, setRoute }: { route: RouteKey; user: SessionUser; setRoute: (route: RouteKey) => void }) {
  const nav = [
    { key: "command" as const, label: "Командный центр", icon: "grid" as const },
    { label: "КОМПАНИЯ", group: true },
    { key: "departments" as const, label: "Отделы", icon: "building" as const },
    { key: "employees" as const, label: "Сотрудники", icon: "team" as const },
    { key: "products" as const, label: "Продукты", icon: "box" as const },
    { label: "ПЛАТФОРМА", group: true },
    { label: "AI", icon: "robot" as const, disabled: true },
    { label: "Интеграции", icon: "plug" as const, disabled: true },
    { divider: true },
    { label: "Настройки", icon: "settings" as const, disabled: true },
  ];
  return (
    <aside className="hub-sidebar">
      <button className="hub-brand" type="button" onClick={() => setRoute("command")}>
        <div className="hub-brand-mark"><PulseIcon /></div>
        <div><strong>Edevs Hub</strong><span>Уровень компании</span></div>
      </button>
      <nav className="hub-nav">
        {nav.map((item, index) => {
          if ("group" in item) return <div className="hub-nav-group" key={item.label}>{item.label}</div>;
          if ("divider" in item) return <div className="hub-nav-divider" key={index} />;
          const nextRoute = "key" in item ? item.key : null;
          const active = nextRoute === route || (nextRoute === "employees" && route === "employeeDetail");
          return (
            <button className={`hub-nav-item ${active ? "is-active" : ""}`} disabled={item.disabled} key={item.label} onClick={() => nextRoute && setRoute(nextRoute)}>
              {active && <span className="active-bar" />}
              <Icon name={item.icon} />
              {item.label}
            </button>
          );
        })}
      </nav>
      <button className={`profile-link ${route === "profile" ? "is-active" : ""}`} onClick={() => setRoute("profile")}>
        <Avatar user={user} />
        <span><strong>{user.fullName || user.email}</strong><small>{user.role}</small></span>
      </button>
    </aside>
  );
}
