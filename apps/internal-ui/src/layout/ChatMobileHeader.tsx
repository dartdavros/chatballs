import { Dropdown } from "antd";
import { useState } from "react";

import type { RouteKey, SessionUser } from "../types";
import { Icon, LogoIcon } from "../shared/icons";
import { Avatar } from "../shared/ui";
import { defaultRoute } from "../auth/access";

// Мобильная шапка экрана списка (дизайн-базлайн v2, кадр M1): логотип +
// организация слева, аватар с меню профиля справа. Видна только на ≤768px —
// сайдбар на мобильном чате скрыт.
export function ChatMobileHeader({ user, setRoute, onLogout }: { user: SessionUser; setRoute: (route: RouteKey) => void; onLogout: () => void }) {
  const [open, setOpen] = useState(false);
  const menuItems = [
    { key: "profile", label: <button type="button" onClick={() => setRoute("profile")}><Icon name="user" size={15} />Профиль</button> },
    { key: "settings", label: <button type="button" onClick={() => setRoute("settings")}><Icon name="settings" size={15} />Настройки</button> },
    { type: "divider" as const },
    { key: "logout", label: <button type="button" className="danger" onClick={onLogout}><Icon name="logout" size={15} />Выйти</button> },
  ];
  return (
    <div className="chat-mobile-header">
      <button className="chat-mobile-brand" type="button" onClick={() => setRoute(defaultRoute(user))}>
        <span className={`hub-brand-mark ${user.organizationLogoUrl ? "has-logo" : ""}`}>
          {user.organizationLogoUrl ? <img src={user.organizationLogoUrl} alt="" /> : <LogoIcon />}
        </span>
        <strong>{user.organizationName || "Chatbolls"}</strong>
      </button>
      <Dropdown menu={{ items: menuItems }} open={open} onOpenChange={setOpen} trigger={["click"]} placement="bottomRight" overlayClassName="app-dropdown is-wide">
        <button className="chat-mobile-avatar" type="button" aria-label="Меню пользователя"><Avatar user={user} /></button>
      </Dropdown>
    </div>
  );
}
