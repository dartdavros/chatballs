import type { RouteKey, SessionUser } from "../types";
import { Icon } from "../shared/icons";
import { canAccess } from "../auth/access";
import { SidebarUserMenu } from "./SidebarUserMenu";

// SPEC-HUB-0010 §8.1: вся внутренняя support-навигация живёт в workspace отдела.
// Зеркало SalesSidebar (переиспользование layout/структуры), переиспользует
// существующие CSS-классы sales-workspace-sidebar/nav — дизайн baseline.
export function SupportSidebar({ route, user, setRoute, onLogout, waitingCount = 0 }: { route: RouteKey; user: SessionUser; setRoute: (route: RouteKey) => void; onLogout: () => void; waitingCount?: number }) {
  const nav = [
    { key: "supportOverview" as const, label: "Обзор", icon: "grid" as const },
    { key: "supportDialogs" as const, label: "Диалоги", icon: "message" as const, badge: waitingCount > 0 ? String(waitingCount) : undefined },
    { key: "supportPortals" as const, label: "Порталы", icon: "folder" as const },
  ];
  return (
    <aside className="hub-sidebar sales-workspace-sidebar">
      {canAccess(user, "command") && (
        <div className="sales-sidebar-back-wrap">
          <button className="sales-sidebar-back" type="button" onClick={() => setRoute("command")}><Icon name="arrow" size={16} />Назад</button>
        </div>
      )}
      <div className="sales-sidebar-title">
        <div className="sales-sidebar-icon"><Icon name="wrench" size={19} /></div>
        <div><strong>Поддержка</strong><span>Рабочее пространство</span></div>
      </div>
      <nav className="hub-nav sales-workspace-nav">
        {nav.map((item) => {
          if (!canAccess(user, item.key)) return null;
          const active = item.key === route || (
            item.key === "supportPortals" && route === "supportPortalDetail"
          );
          return (
            <button className={`hub-nav-item ${active ? "is-active" : ""}`} type="button" onClick={() => setRoute(item.key)} key={item.label}>
              {active && <span className="active-bar" />}
              <Icon name={item.icon} />
              {item.label}
              {item.badge && <b>{item.badge}</b>}
            </button>
          );
        })}
      </nav>
      <SidebarUserMenu user={user} route={route} setRoute={setRoute} onLogout={onLogout} />
    </aside>
  );
}
