import { Dropdown } from "antd";
import { useState } from "react";

import type { RouteKey, SessionUser } from "../types";
import { Icon } from "../shared/icons";
import { Avatar, roleLabel } from "../shared/ui";

export function SidebarUserMenu({ user, route, setRoute, onLogout }: { user: SessionUser; route: RouteKey; setRoute: (route: RouteKey) => void; onLogout: () => void }) {
  const [open, setOpen] = useState(false);
  const active = route === "profile" || route === "settings";
  const menuItems = [
    { key: "profile", label: <button type="button" onClick={() => setRoute("profile")}><Icon name="user" size={15} />Профиль</button> },
    { key: "settings", label: <button type="button" onClick={() => setRoute("settings")}><Icon name="settings" size={15} />Настройки</button> },
    { type: "divider" as const },
    { key: "logout", label: <button type="button" className="danger" onClick={onLogout}><Icon name="logout" size={15} />Выйти</button> },
  ];
  return (
    <Dropdown menu={{ items: menuItems }} open={open} onOpenChange={setOpen} trigger={["click"]} placement="topLeft" overlayClassName="app-dropdown is-wide">
      <button className={`profile-link ${active ? "is-active" : ""}`} type="button" aria-label="Меню пользователя">
        <Avatar user={user} />
        <span><strong>{user.fullName || user.email}</strong><small>{roleLabel(user.role)}</small></span>
        <Icon name="chevron" size={16} />
      </button>
    </Dropdown>
  );
}
