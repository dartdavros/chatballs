import { Dropdown } from "antd";
import { useState } from "react";

import type { RouteKey, SessionUser } from "../types";
import { Icon } from "../shared/icons";
import { Avatar, roleLabel } from "../shared/ui";

export function SidebarUserMenu({ user, route, setRoute, onLogout, unreadCount = 0, onOpenNotifications }: { user: SessionUser; route: RouteKey; setRoute: (route: RouteKey) => void; onLogout: () => void; unreadCount?: number; onOpenNotifications?: () => void }) {
  const [open, setOpen] = useState(false);
  const active = route === "profile";
  const menuItems = [
    ...(onOpenNotifications
      ? [{ key: "notifications", label: <button type="button" onClick={onOpenNotifications}><Icon name="bell" size={15} />Уведомления{unreadCount > 0 && <b className="profile-menu-badge">{unreadCount > 99 ? "99+" : unreadCount}</b>}</button> }]
      : []),
    // «Настройки» — настройки системы, они в навигации, а не в меню пользователя.
    { key: "profile", label: <button type="button" onClick={() => setRoute("profile")}><Icon name="user" size={15} />Профиль</button> },
    { type: "divider" as const },
    { key: "logout", label: <button type="button" className="danger" onClick={onLogout}><Icon name="logout" size={15} />Выйти</button> },
  ];
  return (
    <Dropdown menu={{ items: menuItems }} open={open} onOpenChange={setOpen} trigger={["click"]} placement="topLeft" overlayClassName="app-dropdown is-wide">
      <button className={`profile-link ${active ? "is-active" : ""}`} type="button" aria-label="Меню пользователя">
        <span className="profile-avatar"><Avatar user={user} /><i /></span>
        <span><strong>{user.fullName || user.email}</strong><small>{roleLabel(user.role)} · {user.email}</small></span>
        <span className="profile-more">{unreadCount > 0 && <i className="profile-unread" />}<Icon name="more" size={16} /></span>
      </button>
    </Dropdown>
  );
}
