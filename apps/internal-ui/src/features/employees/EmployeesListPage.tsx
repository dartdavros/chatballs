import { useState } from "react";

import { hasCapability } from "../../auth/access";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import type { Employee, EmployeeGroup, RouteKey, SessionUser } from "../../types";
import { EmployeeCreateDrawer } from "./EmployeeCreateDrawer";
import { EmployeePasswordDialog } from "./EmployeePasswordDialog";
import { EmployeeTable } from "./EmployeeTable";
import { EmployeesFilters } from "./EmployeesFilters";
import { blockEmployee, resetEmployeePassword, terminateEmployeeSessions, type IssuedPassword } from "./api";
import { filterEmployees, type EmployeeRoleFilter } from "./model";

// Список сотрудников (дизайн-базлайн v2, «Сотрудники Baseline», кадры E1/E2).

export function EmployeesPage({ groups, employees, reload, openEmployee, user }: {
  groups: EmployeeGroup[];
  employees: Employee[];
  reload: () => void;
  openEmployee: (employee: Employee) => void;
  setRoute: (route: RouteKey) => void;
  user: SessionUser;
}) {
  const [role, setRole] = useState<EmployeeRoleFilter>("all");
  const [groupId, setGroupId] = useState<number | "all">("all");
  const [query, setQuery] = useState("");
  const [menuId, setMenuId] = useState<number | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [issued, setIssued] = useState<IssuedPassword | null>(null);
  const [error, setError] = useState("");
  const canManage = hasCapability(user, "employees.manage");
  const filtered = filterEmployees(employees, role, groupId, query);

  function resetFilters() {
    setQuery(""); setRole("all"); setGroupId("all"); setMenuId(null);
  }

  async function run(action: () => Promise<void>) {
    setError("");
    try {
      await action();
      reload();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось выполнить действие");
    }
  }

  return (
    <div className="employees-page">
      <header className="employees-header">
        <div>
          <h2>Сотрудники</h2>
          <p>Роли и группы · показано <b>{filtered.length}</b> из {employees.length}</p>
        </div>
        {canManage && (
          <Button className="employees-create" variant="primary" icon="team" iconSize={16} onClick={() => setCreateOpen(true)}>Добавить сотрудника</Button>
        )}
      </header>

      <EmployeesFilters
        groupId={groupId}
        groups={groups}
        query={query}
        role={role}
        resetFilters={resetFilters}
        setGroupId={(value) => { setGroupId(value); setMenuId(null); }}
        setQuery={(value) => { setQuery(value); setMenuId(null); }}
        setRole={(value) => { setRole(value); setMenuId(null); }}
      />

      {error && <div className="employees-error"><Icon name="alert" size={16} strokeWidth={1.8} />{error}</div>}

      <EmployeeTable
        employees={filtered}
        groups={groups}
        menuId={menuId}
        onBlock={(employee) => void run(() => blockEmployee(employee.id, !employee.isBlocked))}
        onResetPassword={(employee) => void run(async () => { setIssued(await resetEmployeePassword(employee.id, "show")); })}
        onTerminateSessions={(employee) => void run(() => terminateEmployeeSessions(employee.id))}
        openEmployee={openEmployee}
        setMenuId={setMenuId}
        total={employees.length}
      />

      {createOpen && (
        <EmployeeCreateDrawer
          groups={groups}
          onClose={() => setCreateOpen(false)}
          onCreated={(password) => { setCreateOpen(false); reload(); if (password) setIssued(password); }}
        />
      )}
      {issued && <EmployeePasswordDialog issued={issued} onClose={() => setIssued(null)} />}
    </div>
  );
}
