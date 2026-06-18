import type { Employee } from "../../types";
import { Icon } from "../../shared/icons";
import { Avatar, EmptyState, RoleBadge, StatusPill } from "../../shared/ui";
import { employeeDetails, employeeStatusKey } from "./model";

export function EmployeeTable({
  block,
  employees,
  menuId,
  openEmployee,
  setMenuId,
  total,
}: {
  block: (employee: Employee) => void;
  employees: Employee[];
  menuId: number | null;
  openEmployee: (employee: Employee) => void;
  setMenuId: (id: number | null) => void;
  total: number;
}) {
  return (
    <div className="table-card employees-card">
      <div className="table-scroll">
        <table className="baseline-table employees-table">
          <thead><tr><th>СОТРУДНИК</th><th>РОЛЬ</th><th>ОТДЕЛ</th><th>СТАТУС</th><th>ПОСЛЕДНИЙ ВХОД</th><th className="numeric">ДИАЛОГИ</th><th /></tr></thead>
          <tbody>
            {employees.map((employee) => <EmployeeRow employee={employee} block={block} openEmployee={openEmployee} menuId={menuId} setMenuId={setMenuId} key={employee.id} />)}
          </tbody>
        </table>
      </div>
      {!employees.length && <EmptyState title="Сотрудники не найдены" />}
      <div className="employees-footer">
        <span>Показано {employees.length} из {total}</span>
        <span>Сессии и пароли управляются в карточке сотрудника</span>
      </div>
    </div>
  );
}

function EmployeeRow({ employee, block, openEmployee, menuId, setMenuId }: { employee: Employee; block: (employee: Employee) => void; openEmployee: (employee: Employee) => void; menuId: number | null; setMenuId: (id: number | null) => void }) {
  const details = employeeDetails(employee);
  const dialogs = String(details.workload.activeDialogs);
  const status = employeeStatusKey(employee);
  const menuOpen = menuId === employee.id;
  const open = () => {
    setMenuId(null);
    openEmployee(employee);
  };
  return (
    <tr>
      <td><div className="person-cell"><Avatar employee={employee} /><button className="person-link" type="button" onClick={open}><strong>{employee.fullName || employee.email}</strong><small>{employee.email}</small></button></div></td>
      <td><RoleBadge role={employee.role} /></td>
      <td>{employee.department === "sales" ? "Продажи" : "—"}</td>
      <td><StatusPill status={status} /></td>
      <td>{details.account.lastLogin}</td>
      <td className={`numeric ${dialogs === "0" ? "muted-number" : ""}`}>{dialogs}</td>
      <td className="row-actions">
        <button className="row-menu-button" aria-label="Действия сотрудника" onClick={() => setMenuId(menuOpen ? null : employee.id)}><Icon name="more" /></button>
        {menuOpen && (
          <div className="row-menu">
            <button type="button" onClick={open}><Icon name="external" size={15} />Открыть карточку</button>
            <a href="#" onClick={(event) => event.preventDefault()}><Icon name="logout" size={15} />Завершить сессии</a>
            <a href="#" onClick={(event) => event.preventDefault()}><Icon name="key" size={15} />Сбросить пароль</a>
            <span />
            <button className={employee.isBlocked ? "success" : "danger"} onClick={() => block(employee)} disabled={employee.role === "OWNER" || employee.isBlocked}>{employee.isBlocked ? "Разблокировать" : "Заблокировать"}</button>
          </div>
        )}
      </td>
    </tr>
  );
}
