import { Dropdown } from "antd";
import { useState } from "react";

import type { RouteKey, SessionUser } from "../types";
import { Icon } from "../shared/icons";
import { Avatar } from "../shared/ui";
import { scopeLabel, type DialogScope } from "../features/conversations/ConversationWorkspace";

// Мобильная шапка экрана списка (дизайн-базлайн v2, кадр M1): ☰ и заголовок
// охвата открывают дерево «Диалоги» выезжающим меню; справа — аватар с меню
// профиля. Видна только на ≤768px.

function pluralDialogs(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return `${count} диалог`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return `${count} диалога`;
  return `${count} диалогов`;
}

export function ChatMobileHeader({ user, scope, total, setRoute, onLogout, onOpenMenu }: { user: SessionUser; scope: DialogScope; total: number; setRoute: (route: RouteKey) => void; onLogout: () => void; onOpenMenu: () => void }) {
  const [open, setOpen] = useState(false);
  const menuItems = [
    { key: "profile", label: <button type="button" onClick={() => setRoute("profile")}><Icon name="user" size={15} />Профиль</button> },
    { key: "settings", label: <button type="button" onClick={() => setRoute("settings")}><Icon name="settings" size={15} />Настройки</button> },
    { type: "divider" as const },
    { key: "logout", label: <button type="button" className="danger" onClick={onLogout}><Icon name="logout" size={15} />Выйти</button> },
  ];
  const title = scope.kind === "all" ? "Все диалоги" : scopeLabel(scope);
  return (
    <div className="chat-mobile-header">
      <button className="chat-mobile-menu" type="button" aria-label="Меню" onClick={onOpenMenu}><Icon name="list" size={20} /></button>
      <button className="chat-mobile-title" type="button" onClick={onOpenMenu}>
        <strong><span>{title}</span><Icon name="chevron" size={14} /></strong>
        <small>{user.organizationName || "Chatbolls"} · {pluralDialogs(total)}</small>
      </button>
      <Dropdown menu={{ items: menuItems }} open={open} onOpenChange={setOpen} trigger={["click"]} placement="bottomRight" overlayClassName="app-dropdown is-wide">
        <button className="chat-mobile-avatar" type="button" aria-label="Меню пользователя"><Avatar user={user} /></button>
      </Dropdown>
    </div>
  );
}
