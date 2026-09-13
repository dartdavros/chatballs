import { Dropdown } from "antd";
import type { CSSProperties } from "react";

import type { RouteKey, SessionUser } from "../types";
import type { SettingsSectionKey } from "../features/settings/sections";
import { useResizableWidth } from "../shared/useResizableWidth";
import { Icon, LogoIcon } from "../shared/icons";
import { canCreateOrganization, defaultRoute, isManager } from "../auth/access";
import type { DialogScope } from "../features/conversations/ConversationWorkspace";
import { agentColorOf, groupColorOf, type ConversationCounters } from "../features/conversations/model";
import { LaunchChecklist } from "./LaunchChecklist";
import { SidebarUserMenu } from "./SidebarUserMenu";
import { t } from "../i18n";

// Сайдбар по дизайн-базлайну v2: у менеджера — плоские семь пунктов (A1, KB1) и
// блок «Запуск»; у сотрудника разделов нет (§3) — сайдбар и есть фильтр списка
// диалогов: дерево «Все диалоги · Группы · Агенты» + профиль внизу.

type SidebarLinkProps = {
  activeRoutes?: RouteKey[];
  badge?: string;
  icon: Parameters<typeof Icon>[0]["name"];
  label: string;
  route: RouteKey;
  routeKey: RouteKey;
  setRoute: (route: RouteKey) => void;
};

function SidebarLink({ activeRoutes, badge, icon, label, route, routeKey, setRoute }: SidebarLinkProps) {
  const active = activeRoutes?.includes(route) ?? routeKey === route;
  return (
    <button
      className={`hub-nav-item ${active ? "is-active" : ""}`}
      type="button"
      onClick={() => setRoute(routeKey)}
    >
      <Icon name={icon} />
      {label}
      {badge && <b className="hub-nav-badge">{badge}</b>}
    </button>
  );
}

export function Sidebar({
  route,
  user,
  setRoute,
  openSettings,
  onLogout,
  onSwitchOrganization,
  waitingCount = 0,
  chatScope,
  setChatScope,
  chatCounters,
  unreadCount = 0,
  onOpenNotifications,
  expanded: railExpanded,
  setExpanded: setRailExpanded,
}: {
  route: RouteKey;
  user: SessionUser;
  setRoute: (route: RouteKey) => void;
  openSettings: (section: SettingsSectionKey | null) => void;
  onLogout: () => void;
  onSwitchOrganization: (organizationPublicId: string) => void;
  waitingCount?: number;
  chatScope: DialogScope;
  setChatScope: (scope: DialogScope) => void;
  chatCounters: ConversationCounters | null;
  unreadCount?: number;
  onOpenNotifications?: () => void;
  expanded: boolean;
  setExpanded: (expanded: boolean) => void;
}) {
  // Ширина сайдбара: тянется за правый край (180–320px), запоминается в браузере.
  const sidebarWidth = useResizableWidth("sidebar", { fallback: 220, min: 180, max: 320 });
  const manager = isManager(user);
  // Кадр S2: на ≤1024px сайдбар сжимается в рейку 60px; «развернуть»
  // раскрывает полный сайдбар поверх контента (состояние — в Shell, его же
  // открывает ☰ мобильной шапки чата, кадр M1).
  const initials = (user.fullName || user.email)
    .split(/\s+/)
    .map((part) => part[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <aside className={`hub-sidebar ${railExpanded ? "is-rail-expanded" : ""} ${sidebarWidth.dragging ? "is-resizing" : ""}`} style={{ "--sidebar-width": `${sidebarWidth.width}px` } as CSSProperties}>
      <div className="pane-resizer" role="separator" aria-orientation="vertical" aria-label={t("profile.sidebar_width")} title={t("profile.drag_resize_double_click_reset")} onPointerDown={sidebarWidth.onPointerDown} onDoubleClick={sidebarWidth.reset} />
      <div className="hub-rail">
        <div className={`hub-brand-mark ${user.organizationLogoUrl ? "has-logo" : ""}`}>
          {user.organizationLogoUrl ? <img src={user.organizationLogoUrl} alt="" /> : <LogoIcon />}
        </div>
        <button
          className={`hub-rail-button ${route === "chat" ? "is-active" : ""}`}
          title={t("common.chat")}
          type="button"
          onClick={() => setRoute("chat")}
        >
          <Icon name="message" size={18} />
        </button>
        <button className="hub-rail-button" title={t("profile.expand")} type="button" onClick={() => setRailExpanded(true)}>
          <Icon name="chevron" size={17} />
        </button>
        <div className="hub-rail-spacer" />
        <button className="hub-rail-avatar" title={user.fullName || user.email} type="button" onClick={() => setRailExpanded(true)}>
          {initials}
        </button>
      </div>
      {railExpanded && <button className="hub-rail-backdrop" aria-label={t("profile.collapse_menu")} type="button" onClick={() => setRailExpanded(false)} />}
      <div className="hub-sidebar-body" onClick={() => setRailExpanded(false)}>
      <div className="hub-brand">
        <button className={`hub-brand-mark ${user.organizationLogoUrl ? "has-logo" : ""}`} type="button" aria-label={t("profile.go_start_page")} onClick={() => setRoute(defaultRoute(user))}>
          {user.organizationLogoUrl
            ? <img src={user.organizationLogoUrl} alt="" />
            : <LogoIcon />}
        </button>
        {/* Переключатель организации (дизайн-базлайн v2, A1): все организации
            человека, текущая отмечена; выбор другой открывает её стартовый экран. */}
        <Dropdown
          trigger={["click"]}
          placement="bottomLeft"
          overlayClassName="app-dropdown is-wide"
          menu={{
            items: [
              ...user.memberships.map((membership) => ({
                key: membership.organizationPublicId,
                label: (
                  <button
                    type="button"
                    className={membership.organizationPublicId === user.organizationPublicId ? "is-checked" : ""}
                    onClick={() => {
                      if (membership.organizationPublicId !== user.organizationPublicId) {
                        onSwitchOrganization(membership.organizationPublicId);
                      }
                    }}
                  >
                    <Icon name="building" size={15} />
                    {membership.organizationName || "Chatballs"}
                  </button>
                ),
              })),
              // «Добавить организацию» — внизу списка, отделена чертой: ведёт на
              // страницу создания, где человек становится владельцем новой.
              ...(canCreateOrganization(user)
                ? [
                  { type: "divider" as const, key: "add-divider" },
                  {
                    key: "add-organization",
                    label: (
                      <button type="button" className="hub-brand-add" onClick={() => setRoute("organizationCreate")}>
                        <span className="hub-brand-add-icon"><Icon name="plus" size={11} strokeWidth={2.4} /></span>
                        {t("organizations.add")}
                      </button>
                    ),
                  },
                ]
                : []),
            ],
          }}
        >
          <button className="hub-brand-switch" type="button" title={t("profile.switch_organization")}>
            <span>{user.organizationName || "Chatballs"}</span>
            <Icon name="chevron" size={14} />
          </button>
        </Dropdown>
      </div>
      {manager ? (
        <nav className="hub-nav">
          <SidebarLink icon="message" label={t("common.chat")} badge={waitingCount > 0 ? String(waitingCount) : undefined} route={route} routeKey="chat" setRoute={setRoute} />
          <SidebarLink activeRoutes={["salesClients", "salesClientDetail"]} icon="user" label={t("common.contacts")} route={route} routeKey="salesClients" setRoute={setRoute} />
          <SidebarLink activeRoutes={["agents", "agentDetail"]} icon="robot" label={t("common.agents")} route={route} routeKey="agents" setRoute={setRoute} />
          <SidebarLink activeRoutes={["employees", "employeeDetail"]} icon="team" label={t("common.operators")} route={route} routeKey="employees" setRoute={setRoute} />
          <SidebarLink activeRoutes={["supportPortals", "supportPortalDetail", "supportPortalSettings"]} icon="globe" label={t("common.portals")} route={route} routeKey="supportPortals" setRoute={setRoute} />
          <SidebarLink activeRoutes={["knowledge", "knowledgeDetail", "knowledgeCreate", "knowledgeEdit", "knowledgeCategories", "knowledgeImport"]} icon="book" label={t("common.knowledge_base")} route={route} routeKey="knowledge" setRoute={setRoute} />
          <SidebarLink activeRoutes={["settings", "administrationAudit"]} icon="settings" label={t("common.settings")} route={route} routeKey="settings" setRoute={setRoute} />
        </nav>
      ) : route === "profile" ? (
        /* Кадр P2: на «Профиле» у сотрудника сайдбар без навигации — фильтровать
           нечего, дерево диалогов относится только к чату. */
        null
      ) : (
        <ChatScopeTree
          route={route}
          scope={chatScope}
          counters={chatCounters}
          setScope={(scope) => {
            setChatScope(scope);
            setRoute("chat");
          }}
        />
      )}
      {manager && <LaunchChecklist user={user} setRoute={setRoute} openSettings={openSettings} />}
      <SidebarUserMenu user={user} route={route} setRoute={setRoute} onLogout={onLogout} unreadCount={unreadCount} onOpenNotifications={onOpenNotifications} />
      </div>
    </aside>
  );
}

// Дерево «Диалоги» сотрудника (кадры A-H): пункты — это охват списка чата.
function ChatScopeTree({
  route,
  scope,
  counters,
  setScope,
}: {
  route: RouteKey;
  scope: DialogScope;
  counters: ConversationCounters | null;
  setScope: (scope: DialogScope) => void;
}) {
  const inChat = route === "chat";
  const isActive = (candidate: DialogScope) =>
    inChat
    && scope.kind === candidate.kind
    && (scope.kind !== "group" || candidate.kind !== "group" || scope.id === candidate.id)
    && (scope.kind !== "agent" || candidate.kind !== "agent" || scope.id === candidate.id);

  return (
    <nav className="hub-nav chat-scope-tree">
      <div className="chat-scope-head"><Icon name="message" size={17} /><span>{t("common.conversations")}</span></div>
      <button
        className={`chat-scope-item is-top ${isActive({ kind: "all" }) ? "is-active" : ""}`}
        type="button"
        onClick={() => setScope({ kind: "all" })}
      >
        <Icon name="inbox" size={15} />
        <span>{t("profile.all_conversations")}</span>
        {counters && <small>{counters.all}</small>}
      </button>
      {counters && (
        <>
          <div className="chat-scope-section"><Icon name="team" size={15} /><span>{t("common.groups")}</span></div>
          {counters.groups.map((group) => (
            <button
              className={`chat-scope-item is-nested ${isActive({ kind: "group", id: group.id, label: group.name }) ? "is-active" : ""}`}
              key={group.id}
              type="button"
              onClick={() => setScope({ kind: "group", id: group.id, label: group.name })}
            >
              <i className="chat-scope-dot" style={{ background: groupColorOf(group.id, group.color) }} />
              <span>{group.name}</span>
              <small>{group.count}</small>
            </button>
          ))}
          {counters.groups.length > 0 && (
            <button
              className={`chat-scope-item is-nested ${isActive({ kind: "ungrouped" }) ? "is-active" : ""}`}
              type="button"
              onClick={() => setScope({ kind: "ungrouped" })}
            >
              <i className="chat-scope-dot is-muted" />
              <span>{t("common.no_group")}</span>
              <small>{counters.ungrouped}</small>
            </button>
          )}
        </>
      )}
      {counters && (
        <>
          <div className="chat-scope-section"><Icon name="robot" size={15} /><span>{t("common.agents")}</span></div>
          {counters.agents.map((agent) => (
            <button
              className={`chat-scope-item is-nested ${isActive({ kind: "agent", id: agent.id, label: agent.name }) ? "is-active" : ""}`}
              key={agent.id}
              type="button"
              onClick={() => setScope({ kind: "agent", id: agent.id, label: agent.name })}
            >
              <span className="chat-scope-agent" style={{ color: agentColorOf(agent.id), background: `color-mix(in srgb, ${agentColorOf(agent.id)} 16%, var(--surface-card))` }}><Icon name="robot" size={11} /></span>
              <span>{agent.name}</span>
              <small>{agent.count}</small>
            </button>
          ))}
        </>
      )}
    </nav>
  );
}
