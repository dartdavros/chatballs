import { Dropdown } from "antd";
import { useState } from "react";

import type { RouteKey, SessionUser } from "../types";
import { Icon } from "../shared/icons";
import { Avatar } from "../shared/ui";
import { scopeLabel, type DialogScope } from "../features/conversations/ConversationWorkspace";
import { t, tn } from "../i18n";

// Мобильная шапка экрана списка (дизайн-базлайн v2, кадр M1): ☰ и заголовок
// охвата открывают дерево «Диалоги» выезжающим меню; справа — аватар с меню
// профиля. Видна только на ≤768px.

export function ChatMobileHeader({ user, scope, total, setRoute, onLogout, onOpenMenu }: { user: SessionUser; scope: DialogScope; total: number; setRoute: (route: RouteKey) => void; onLogout: () => void; onOpenMenu: () => void }) {
  const [open, setOpen] = useState(false);
  const menuItems = [
    { key: "profile", label: <button type="button" onClick={() => setRoute("profile")}><Icon name="user" size={15} />{t("common.profile")}</button> },
    { type: "divider" as const },
    { key: "logout", label: <button type="button" className="danger" onClick={onLogout}><Icon name="logout" size={15} />{t("common.sign_out")}</button> },
  ];
  const title = scope.kind === "all" ? t("profile.all_conversations") : scopeLabel(scope);
  return (
    <div className="chat-mobile-header">
      <button className="chat-mobile-menu" type="button" aria-label={t("profile.menu")} onClick={onOpenMenu}><Icon name="list" size={20} /></button>
      <button className="chat-mobile-title" type="button" onClick={onOpenMenu}>
        <strong><span>{title}</span><Icon name="chevron" size={14} /></strong>
        <small>{user.organizationName || "Chatballs"} · {tn("plural.conversations", total)}</small>
      </button>
      <Dropdown menu={{ items: menuItems }} open={open} onOpenChange={setOpen} trigger={["click"]} placement="bottomRight" overlayClassName="app-dropdown is-wide">
        <button className="chat-mobile-avatar" type="button" aria-label={t("profile.user_menu")}><Avatar user={user} /></button>
      </Dropdown>
    </div>
  );
}
