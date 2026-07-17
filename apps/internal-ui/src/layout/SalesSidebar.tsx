import type { RouteKey, SessionUser } from "../types";
import { Icon } from "../shared/icons";
import { Avatar } from "../shared/ui";
import { canAccess } from "../auth/access";

export function SalesSidebar({ route, user, setRoute, waitingCount = 0 }: { route: RouteKey; user: SessionUser; setRoute: (route: RouteKey) => void; waitingCount?: number }) {
  const nav = [
    { key: "salesOverview" as const, label: "Обзор", icon: "grid" as const },
    { key: "salesDialogs" as const, label: "Диалоги", icon: "message" as const, badge: waitingCount > 0 ? String(waitingCount) : undefined },
    { key: "salesClients" as const, label: "Контакты", icon: "team" as const },
    { key: "salesOrders" as const, label: "Продажи", icon: "cart" as const },
  ];
  return (
    <aside className="hub-sidebar sales-workspace-sidebar">
      {canAccess(user, "command") && (
        <div className="sales-sidebar-back-wrap">
          <button className="sales-sidebar-back" type="button" onClick={() => setRoute("command")}><Icon name="arrow" size={16} />Назад</button>
        </div>
      )}
      <div className="sales-sidebar-title">
        <div className="sales-sidebar-icon"><Icon name="shop" size={19} /></div>
        <div><strong>Продажи</strong><span>Рабочее пространство</span></div>
      </div>
      <nav className="hub-nav sales-workspace-nav">
        {nav.map((item) => {
          const nextRoute = "key" in item ? item.key : null;
          if (nextRoute && !canAccess(user, nextRoute)) return null;
          const active = nextRoute === route || (nextRoute === "salesClients" && route === "salesClientDetail") || (nextRoute === "salesOrders" && route === "salesOrderDetail");
          return (
          <button className={`hub-nav-item ${active ? "is-active" : ""}`} type="button" onClick={() => nextRoute && setRoute(nextRoute)} key={item.label}>
            {active && <span className="active-bar" />}
            <Icon name={item.icon} />
            {item.label}
            {item.badge && <b>{item.badge}</b>}
          </button>
          );
        })}
      </nav>
      <button className="profile-link" onClick={() => setRoute("profile")}>
        <Avatar user={user} />
        <span><strong>{user.fullName || user.email}</strong><small>{user.role}</small></span>
      </button>
    </aside>
  );
}
