import { Dropdown } from "antd";

import type { Employee, EmployeeGroup } from "../../types";
import { Icon } from "../../shared/icons";
import { Avatar, EmptyState } from "../../shared/ui";
import { groupColorOf } from "../conversations/model";
import { employeeAvatarColor, formatLastLogin, roleAccessLabel, roleBadge, statusBadge } from "./model";
import { t } from "../../i18n";

// Таблица сотрудников (дизайн-базлайн v2, «Сотрудники Baseline», кадры E1/E2):
// сотрудник · роль · должность · группы · доступ · статус · последний вход · ⋯.

export function EmployeeTable({
  employees,
  groups,
  menuId,
  onBlock,
  onResetPassword,
  onTerminateSessions,
  openEmployee,
  setMenuId,
  total,
}: {
  employees: Employee[];
  groups: EmployeeGroup[];
  menuId: number | null;
  onBlock: (employee: Employee) => void;
  onResetPassword: (employee: Employee) => void;
  onTerminateSessions: (employee: Employee) => void;
  openEmployee: (employee: Employee) => void;
  setMenuId: (id: number | null) => void;
  total: number;
}) {
  return (
    <div className="employees-table">
      <div className="employees-thead">
        <span>{t("common.operator")}</span>
        <span>{t("common.role")}</span>
        <span>{t("common.position")}</span>
        <span>{t("common.groups")}</span>
        <span>{t("admin.access")}</span>
        <span>{t("common.status")}</span>
        <span>{t("admin.last_sign")}</span>
        <span />
      </div>
      {employees.map((employee) => (
        <EmployeeRow
          employee={employee}
          groups={groups}
          menuOpen={menuId === employee.id}
          onBlock={onBlock}
          onResetPassword={onResetPassword}
          onTerminateSessions={onTerminateSessions}
          openEmployee={openEmployee}
          setMenuId={setMenuId}
          key={employee.id}
        />
      ))}
      {!employees.length && <EmptyState title={t("admin.no_operators_found")} />}
      <div className="employees-foot">
        <small>{t("common.shown_of", { shown: employees.length, total })}</small>
        <small>{t("admin.group_decides_which_conversations_visible_2")}</small>
      </div>
    </div>
  );
}

function EmployeeRow({ employee, groups, menuOpen, onBlock, onResetPassword, onTerminateSessions, openEmployee, setMenuId }: {
  employee: Employee;
  groups: EmployeeGroup[];
  menuOpen: boolean;
  onBlock: (employee: Employee) => void;
  onResetPassword: (employee: Employee) => void;
  onTerminateSessions: (employee: Employee) => void;
  openEmployee: (employee: Employee) => void;
  setMenuId: (id: number | null) => void;
}) {
  const permissions = employee.permissions;
  const role = roleBadge(employee.role);
  const status = statusBadge(employee);
  const open = () => { setMenuId(null); openEmployee(employee); };
  const act = (run: () => void) => { setMenuId(null); run(); };
  // Кадр E2: карточка · сессии · пароль · разделитель · блокировка.
  // Передачи владения в меню строки нет — она только в опасной зоне владельца.
  const menuItems = [
    { key: "open", label: <button type="button" onClick={open}><Icon name="external" size={15} />{t("admin.open_card")}</button> },
    { key: "sessions", disabled: !permissions?.canTerminateSessions, label: <button type="button" onClick={() => act(() => onTerminateSessions(employee))}><Icon name="logout" size={15} />{t("admin.end_sessions")}</button> },
    { key: "password", disabled: !permissions?.canResetPassword, label: <button type="button" onClick={() => act(() => onResetPassword(employee))}><Icon name="lock" size={15} />{t("admin.reset_password")}</button> },
    { type: "divider" as const },
    {
      key: "block",
      disabled: employee.isBlocked ? !permissions?.canUnblock : !permissions?.canBlock,
      label: (
        <button className={employee.isBlocked ? "success" : "danger"} type="button" onClick={() => act(() => onBlock(employee))}>
          <Icon name="lock" size={15} />{employee.isBlocked ? t("admin.unblock") : t("admin.block")}
        </button>
      ),
    },
  ];

  return (
    <div className={`employees-row ${employee.isBlocked ? "is-blocked" : ""}`} role="button" tabIndex={0} onClick={open} onKeyDown={(event) => { if (event.key === "Enter") open(); }}>
      <div className="employees-person">
        <Avatar employee={employee} background={employeeAvatarColor(employee)} />
        <span>
          <strong>{employee.fullName || employee.email}</strong>
          <small>{employee.email}</small>
        </span>
      </div>
      <b className="employees-badge" style={{ background: role.bg, color: role.color }}>{role.text}</b>
      <span className="employees-position">{employee.positionTitle}</span>
      <div className="employees-groups">
        {employee.groups.length === 0
          ? <span className="employees-nogroup">{t("common.no_group")}</span>
          : employee.groups.map((group) => (
            <span className="employees-group" key={group.id}>
              <i style={{ background: groupColorOf(group.id, groups.find((item) => item.id === group.id)?.color) }} />
              {group.name}
            </span>
          ))}
      </div>
      <span className={`employees-access ${employee.role === "EMPLOYEE" ? "is-limited" : ""}`}>{roleAccessLabel(employee)}</span>
      <b className="employees-badge has-dot" style={{ background: status.bg, color: status.color }}><i />{status.text}</b>
      <span className="employees-login">{formatLastLogin(employee.lastLogin)}</span>
      <Dropdown menu={{ items: menuItems }} open={menuOpen} onOpenChange={(next) => setMenuId(next ? employee.id : null)} trigger={["click"]} overlayClassName="app-dropdown is-employee-menu">
        <button className={`employees-row-menu ${menuOpen ? "is-open" : ""}`} type="button" aria-label={t("common.actions_for", { name: employee.fullName || employee.email })} title={t("common.actions")} onClick={(event) => event.stopPropagation()}>
          <Icon name="more" size={16} />
        </button>
      </Dropdown>
    </div>
  );
}
