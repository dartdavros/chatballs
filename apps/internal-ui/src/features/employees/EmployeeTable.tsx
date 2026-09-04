import { Dropdown } from "antd";

import type { Employee } from "../../types";
import { Icon } from "../../shared/icons";
import { Avatar, EmptyState, RoleBadge, StatusPill } from "../../shared/ui";
import { employeeStatusKey, formatLastLogin, groupsLabel, roleAccessLabel } from "./model";

export function EmployeeTable({
  employees,
  menuId,
  onTransfer,
  openEmployee,
  setMenuId,
  total,
}: {
  employees: Employee[];
  menuId: number | null;
  onTransfer: () => void;
  openEmployee: (employee: Employee) => void;
  setMenuId: (id: number | null) => void;
  total: number;
}) {
  return (
    <div className="table-card employees-card">
      <div className="table-scroll">
        <table className="baseline-table employees-table">
          <thead><tr><th>СОТРУДНИК</th><th>РОЛЬ</th><th>ДОЛЖНОСТЬ</th><th>ГРУППЫ</th><th>ДОСТУП</th><th>СТАТУС</th><th>ПОСЛЕДНИЙ ВХОД</th><th /></tr></thead>
          <tbody>
            {employees.map((employee) => (
              <EmployeeRow
                employee={employee}
                menuOpen={menuId === employee.id}
                onTransfer={onTransfer}
                openEmployee={openEmployee}
                setMenuId={setMenuId}
                key={employee.id}
              />
            ))}
          </tbody>
        </table>
      </div>
      {!employees.length && <EmptyState title="Сотрудники не найдены" />}
      <div className="employees-footer">
        <span>Показано {employees.length} из {total}</span>
        <span>Группа задаёт только видимость диалогов и не выдаёт прав</span>
      </div>
    </div>
  );
}

function EmployeeRow({ employee, menuOpen, onTransfer, openEmployee, setMenuId }: {
  employee: Employee;
  menuOpen: boolean;
  onTransfer: () => void;
  openEmployee: (employee: Employee) => void;
  setMenuId: (id: number | null) => void;
}) {
  // Destructive row actions stay visual until their baseline confirmation states are approved.
  const permissions = employee.permissions;
  const manageable = Boolean(permissions?.canBlock || permissions?.canUnblock || permissions?.canResetPassword || permissions?.canTerminateSessions);
  const open = () => { setMenuId(null); openEmployee(employee); };
  const menuItems = [
    { key: "open", label: <button type="button" onClick={open}><Icon name="external" size={15} />Открыть карточку</button> },
    ...(permissions?.canTransferOwnership ? [{ key: "transfer", label: <button type="button" onClick={onTransfer}><Icon name="split" size={15} />Передать владение</button> }] : []),
    ...(manageable ? [
      { key: "sessions", disabled: !permissions?.canTerminateSessions, label: <button type="button"><Icon name="logout" size={15} />Завершить сессии</button> },
      { key: "password", disabled: !permissions?.canResetPassword, label: <button type="button"><Icon name="lock" size={15} />Сбросить пароль</button> },
      { type: "divider" as const },
      { key: "block", disabled: employee.isBlocked ? !permissions?.canUnblock : !permissions?.canBlock, label: <button className={employee.isBlocked ? "success" : "danger"} type="button">{employee.isBlocked ? "Разблокировать" : "Заблокировать"}</button> },
    ] : []),
  ];
  return (
    <tr>
      <td><div className="person-cell"><Avatar employee={employee} /><button className="person-link" type="button" onClick={open}><strong>{employee.fullName || employee.email}</strong><small>{employee.email}</small></button></div></td>
      <td><RoleBadge role={employee.role} /></td>
      <td>{employee.positionTitle}</td>
      <td>{groupsLabel(employee)}</td>
      <td>{roleAccessLabel(employee)}</td>
      <td><StatusPill status={employeeStatusKey(employee)} /></td>
      <td className="employee-last-login">{formatLastLogin(employee.lastLogin)}</td>
      <td className="row-actions">
        <Dropdown menu={{ items: menuItems }} open={menuOpen} onOpenChange={(next) => setMenuId(next ? employee.id : null)} trigger={["click"]} overlayClassName="app-dropdown is-wide">
          <button className="row-menu-button" type="button" aria-label={`Действия: ${employee.fullName || employee.email}`}><Icon name="more" /></button>
        </Dropdown>
      </td>
    </tr>
  );
}
