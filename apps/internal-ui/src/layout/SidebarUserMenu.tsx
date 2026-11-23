import { Dropdown } from "antd";
import { useState } from "react";

import { canViewRuleJournal, isManager } from "../auth/access";
import type { RouteKey, SessionUser } from "../types";
import { Icon } from "../shared/icons";
import { Avatar } from "../shared/ui";
import { t } from "../i18n";
import { WorkStatusConnectionNotice } from "../features/work-status/WorkStatusConnectionNotice";
import { PresenceDot } from "../features/work-status/WorkStatusLabel";
import { WorkStatusSaveError, WorkStatusSelector } from "../features/work-status/WorkStatusSelector";
import type { OwnWorkStatus } from "../features/work-status/useOwnWorkStatus";

export function SidebarUserMenu({ user, route, setRoute, onLogout, unreadCount = 0, onOpenNotifications, workStatus }: { user: SessionUser; route: RouteKey; setRoute: (route: RouteKey) => void; onLogout: () => void; unreadCount?: number; onOpenNotifications?: () => void; workStatus: OwnWorkStatus }) {
  const [open, setOpen] = useState(false);
  const active = route === "profile";
  const menuItems = [
    ...(!isManager(user) && canViewRuleJournal(user) ? [{ key: "ruleJournal", label: <button type="button" onClick={() => setRoute("ruleJournal")}><Icon name="clock" size={15} />{t("handling_rules.journal_title")}</button> }] : []),
    ...(onOpenNotifications
      ? [{ key: "notifications", label: <button type="button" onClick={onOpenNotifications}><Icon name="bell" size={15} />{t("common.notifications")}{unreadCount > 0 && <b className="profile-menu-badge">{unreadCount > 99 ? "99+" : unreadCount}</b>}</button> }]
      : []),
    // «Настройки» — настройки системы, они в навигации, а не в меню пользователя.
    { key: "profile", label: <button type="button" onClick={() => setRoute("profile")}><Icon name="user" size={15} />{t("common.profile")}</button> },
    // У сотрудника нет «Настроек»: библиотека шаблонов открывается отсюда (кадр N8).
    ...(isManager(user)
      ? []
      : [{ key: "templates", label: <button type="button" onClick={() => setRoute("replyTemplates")}><Icon name="text" size={15} />{t("settings.reply_templates")}</button> }]),
    { type: "divider" as const },
    { key: "logout", label: <button type="button" className="danger" onClick={onLogout}><Icon name="logout" size={15} />{t("common.sign_out")}</button> },
  ];
  return (
    <>
      <WorkStatusConnectionNotice connectionLost={workStatus.connectionLost} />
      {/* Кадр K2: статус и меню пользователя — две отдельные кнопки одного блока. */}
      <div className={`profile-link ${active ? "is-active" : ""}`}>
        <span className="profile-avatar"><Avatar user={user} /><PresenceDot online={workStatus.online} own /></span>
        <span>
          <strong>{user.fullName || user.email}</strong>
          <WorkStatusSelector state={workStatus} organization={user.organizationName} />
        </span>
        <Dropdown menu={{ items: menuItems }} open={open} onOpenChange={setOpen} trigger={["click"]} placement="topLeft" overlayClassName="app-dropdown is-wide">
          <button className="row-menu-button profile-more" type="button" title={t("profile.user_menu")} aria-label={t("profile.user_menu")}>
            {unreadCount > 0 && <i className="profile-unread" />}<Icon name="more" size={16} />
          </button>
        </Dropdown>
      </div>
      <WorkStatusSaveError state={workStatus} />
    </>
  );
}
