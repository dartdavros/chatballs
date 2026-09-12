import { Dropdown } from "antd";
import { useState } from "react";

import type { EmployeeGroup, EmployeeInvitation } from "../../types";
import { Icon } from "../../shared/icons";
import { Avatar } from "../../shared/ui";
import { groupColorOf } from "../conversations/model";
import { formatDate, invitationStatusBadge, roleAccessLabel, roleBadge } from "./model";
import { t } from "../../i18n";

// Строка ожидающего приглашения (кадры E1/E2, статус «Приглашён»): та же
// разметка, что у сотрудника, — роль, должность и группы уже известны, они
// придут вместе с членством после принятия. Карточки у приглашения нет,
// поэтому строка не открывается; меню — отправить ещё раз или отозвать.

export function EmployeeInvitationRow({ invitation, groups, canManage, onResend, onRevoke }: {
  invitation: EmployeeInvitation;
  groups: EmployeeGroup[];
  canManage: boolean;
  onResend: (invitation: EmployeeInvitation) => void;
  onRevoke: (invitation: EmployeeInvitation) => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const role = roleBadge(invitation.role);
  const status = invitationStatusBadge();
  const act = (run: () => void) => { setMenuOpen(false); run(); };
  const menuItems = [
    { key: "resend", disabled: !canManage, label: <button type="button" onClick={() => act(() => onResend(invitation))}><Icon name="mail" size={15} />{t("admin.resend_invitation")}</button> },
    { type: "divider" as const },
    { key: "revoke", disabled: !canManage, label: <button className="danger" type="button" onClick={() => act(() => onRevoke(invitation))}><Icon name="xCircle" size={15} />{t("admin.revoke_invitation")}</button> },
  ];

  return (
    <div className="employees-row is-invited">
      <div className="employees-person">
        <Avatar employee={{ ...invitation, isActive: true, isBlocked: false, mustChangePassword: true, totpRequired: false, totpEnabled: false }} />
        <span>
          <strong>{invitation.fullName || invitation.email}</strong>
          <small>{invitation.email}</small>
        </span>
      </div>
      <b className="employees-badge" style={{ background: role.bg, color: role.color }}>{role.text}</b>
      <span className="employees-position">{invitation.positionTitle}</span>
      <div className="employees-groups">
        {invitation.groups.length === 0
          ? <span className="employees-nogroup">{t("common.no_group")}</span>
          : invitation.groups.map((group) => (
            <span className="employees-group" key={group.id}>
              <i style={{ background: groupColorOf(group.id, groups.find((item) => item.id === group.id)?.color) }} />
              {group.name}
            </span>
          ))}
      </div>
      <span className={`employees-access ${invitation.role === "EMPLOYEE" ? "is-limited" : ""}`}>{roleAccessLabel(invitation)}</span>
      <b className="employees-badge has-dot" style={{ background: status.bg, color: status.color }}><i />{status.text}</b>
      <span className="employees-login">{t("admin.invitation_valid_until", { date: formatDate(invitation.expiresAt) })}</span>
      <Dropdown menu={{ items: menuItems }} open={menuOpen} onOpenChange={setMenuOpen} trigger={["click"]} overlayClassName="app-dropdown is-employee-menu">
        <button className={`employees-row-menu ${menuOpen ? "is-open" : ""}`} type="button" aria-label={t("common.actions_for", { name: invitation.fullName || invitation.email })} title={t("common.actions")} onClick={(event) => event.stopPropagation()}>
          <Icon name="more" size={16} />
        </button>
      </Dropdown>
    </div>
  );
}
