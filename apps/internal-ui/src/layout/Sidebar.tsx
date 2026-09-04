import type { RouteKey, SessionUser } from "../types";
import { Icon, LogoIcon } from "../shared/icons";
import { canAccess, defaultRoute } from "../auth/access";
import { SidebarNavSection, type SidebarNavSectionItem } from "./SidebarNavSection";
import { SidebarUserMenu } from "./SidebarUserMenu";

type SidebarLinkProps = {
  activeRoutes?: RouteKey[];
  disabled?: boolean;
  icon: Parameters<typeof Icon>[0]["name"];
  label: string;
  route: RouteKey;
  routeKey?: RouteKey;
  setRoute: (route: RouteKey) => void;
};

function SidebarLink({ activeRoutes, disabled, icon, label, route, routeKey, setRoute }: SidebarLinkProps) {
  const active = activeRoutes?.includes(route) ?? routeKey === route;
  return (
    <button
      className={`hub-nav-item ${active ? "is-active" : ""}`}
      disabled={disabled}
      type="button"
      onClick={() => routeKey && setRoute(routeKey)}
    >
      {active && <span className="active-bar" />}
      <Icon name={icon} />
      {label}
    </button>
  );
}

const SALES_ITEMS: SidebarNavSectionItem[] = [
  { activeRoutes: ["salesDialogs"], key: "salesDialogs", label: "Диалоги" },
  { activeRoutes: ["salesClients", "salesClientDetail"], key: "salesClients", label: "Контакты" },
];

const SUPPORT_ITEMS: SidebarNavSectionItem[] = [
  { activeRoutes: ["supportOverview"], key: "supportOverview", label: "Обзор" },
  { activeRoutes: ["supportDialogs"], key: "supportDialogs", label: "Диалоги" },
  { activeRoutes: ["supportPortals", "supportPortalDetail"], key: "supportPortals", label: "Порталы" },
];

const AI_ITEMS: SidebarNavSectionItem[] = [
  { activeRoutes: ["aiKnowledge", "aiKnowledgeCreate", "aiKnowledgeDetail"], key: "aiKnowledge", label: "Знания" },
  { activeRoutes: ["aiUsage"], disabled: true, key: "aiUsage", label: "Использование AI" },
];

const ADMINISTRATION_ITEMS: SidebarNavSectionItem[] = [
  {
    activeRoutes: ["administrationOrganization"],
    key: "administrationOrganization",
    label: "Организация",
  },
  {
    activeRoutes: ["administrationSubscription"],
    key: "administrationSubscription",
    label: "Тариф и оплата",
  },
  {
    activeRoutes: ["administrationAudit"],
    key: "administrationAudit",
    label: "Аудит",
  },
];

function visibleItems(user: SessionUser, items: SidebarNavSectionItem[]) {
  return items.filter((item) => canAccess(user, item.key));
}

export function Sidebar({ route, user, setRoute, onLogout, waitingCount = 0 }: { route: RouteKey; user: SessionUser; setRoute: (route: RouteKey) => void; onLogout: () => void; waitingCount?: number }) {
  const sectionStorageKey = (section: string) => (
    `chatbolls.sidebar.${user.organizationPublicId}.${section}.expanded`
  );
  const salesItems = visibleItems(user, SALES_ITEMS).map((item) => (
    item.key === "salesDialogs" && waitingCount > 0
      ? { ...item, badge: String(waitingCount) }
      : item
  ));
  const supportItems = visibleItems(user, SUPPORT_ITEMS);
  const aiItems = visibleItems(user, AI_ITEMS);
  const administrationItems = visibleItems(user, ADMINISTRATION_ITEMS);

  return (
    <aside className="hub-sidebar">
      <button className="hub-brand" type="button" onClick={() => setRoute(defaultRoute(user))}>
        <div className={`hub-brand-mark ${user.organizationLogoUrl ? "has-logo" : ""}`}>
          {user.organizationLogoUrl
            ? <img src={user.organizationLogoUrl} alt="" />
            : <LogoIcon />}
        </div>
        <div><strong>Chatbolls</strong><span>Управление компанией</span></div>
      </button>
      <nav className="hub-nav">
        {canAccess(user, "command") && <SidebarLink icon="grid" label="Обзор" route={route} routeKey="command" setRoute={setRoute} />}
        <div className="hub-nav-group">КОМПАНИЯ</div>
        <SidebarNavSection icon="shop" items={salesItems} label="Клиенты" route={route} setRoute={setRoute} storageKey={sectionStorageKey("sales")} />
        <SidebarNavSection icon="wrench" items={supportItems} label="Поддержка" route={route} setRoute={setRoute} storageKey={sectionStorageKey("support")} />
        {canAccess(user, "employees") && <SidebarLink activeRoutes={["employees", "employeeDetail"]} icon="team" label="Сотрудники" route={route} routeKey="employees" setRoute={setRoute} />}
        {canAccess(user, "agents") && <SidebarLink activeRoutes={["agents", "agentDetail"]} icon="robot" label="Агенты" route={route} routeKey="agents" setRoute={setRoute} />}
        <div className="hub-nav-group">ПЛАТФОРМА</div>
        <SidebarNavSection icon="robot" items={aiItems} label="AI" route={route} setRoute={setRoute} storageKey={sectionStorageKey("ai")} />
        {canAccess(user, "integrations") && <SidebarLink icon="plug" label="Интеграции" route={route} routeKey="integrations" setRoute={setRoute} />}
        <div className="hub-nav-divider" />
        <SidebarNavSection
          icon="settings"
          items={administrationItems}
          label="Администрирование"
          route={route}
          setRoute={setRoute}
          storageKey={sectionStorageKey("administration")}
        />
      </nav>
      <SidebarUserMenu user={user} route={route} setRoute={setRoute} onLogout={onLogout} />
    </aside>
  );
}
