import { useState } from "react";

import { api } from "../../api/client";
import type { Employee, Role } from "../../types";
import { PageHeader } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import { EmployeeTable } from "./EmployeeTable";
import { EmployeesFilters } from "./EmployeesFilters";
import { filterEmployees, type EmployeeStatusFilter } from "./model";

export function EmployeesPage({ employees, reload, openEmployee }: { employees: Employee[]; reload: () => void; openEmployee: (employee: Employee) => void }) {
  const [role, setRole] = useState<"all" | Role>("all");
  const [status, setStatus] = useState<EmployeeStatusFilter>("all");
  const [query, setQuery] = useState("");
  const [menuId, setMenuId] = useState<number | null>(null);
  const filtered = filterEmployees(employees, role, status, query);

  async function block(employee: Employee) {
    if (employee.role === "OWNER" || employee.isBlocked) return;
    await api(`/api/v1/employees/${employee.id}/block/`, { method: "POST" });
    setMenuId(null);
    reload();
  }

  function resetFilters() {
    setQuery("");
    setRole("all");
    setStatus("all");
    setMenuId(null);
  }

  return (
    <>
      {menuId !== null && <button className="menu-scrim" aria-label="Закрыть меню" onClick={() => setMenuId(null)} />}
      <PageHeader
        title="Сотрудники"
        text={<>Доступ к Hub · показано <b>{filtered.length}</b> из {employees.length}</>}
        action={<Button icon="team" iconSize={16} type="button" variant="primary">Добавить сотрудника</Button>}
      />
      <EmployeesFilters
        query={query}
        role={role}
        status={status}
        resetFilters={resetFilters}
        setQuery={(nextQuery) => { setQuery(nextQuery); setMenuId(null); }}
        setRole={(nextRole) => { setRole(nextRole); setMenuId(null); }}
        setStatus={(nextStatus) => { setStatus(nextStatus); setMenuId(null); }}
      />
      <EmployeeTable block={block} employees={filtered} menuId={menuId} openEmployee={openEmployee} setMenuId={setMenuId} total={employees.length} />
    </>
  );
}
