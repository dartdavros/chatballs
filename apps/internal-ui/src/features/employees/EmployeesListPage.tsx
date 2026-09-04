import { useState } from "react";

import { hasCapability } from "../../auth/access";
import { PageHeader } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import type { Employee, EmployeeGroup, RouteKey, SessionUser } from "../../types";
import { EmployeeCreateDrawer } from "./EmployeeCreateDrawer";
import { EmployeeTable } from "./EmployeeTable";
import { EmployeesFilters } from "./EmployeesFilters";
import { filterEmployees, type EmployeeRoleFilter } from "./model";
import { OwnershipTransferModal } from "./OwnershipTransferModal";

export function EmployeesPage({ groups, employees, reload, openEmployee, setRoute, user }: {
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
  const [transferOpen, setTransferOpen] = useState(false);
  const canManage = hasCapability(user, "employees.manage");
  const filtered = filterEmployees(employees, role, groupId, query);

  function resetFilters() {
    setQuery(""); setRole("all"); setGroupId("all"); setMenuId(null);
  }

  return (
    <>
      <PageHeader
        title="Сотрудники"
        text={<>Роли и группы · показано <b>{filtered.length}</b> из {employees.length}</>}
        action={canManage && <div className="employee-page-actions"><Button icon="team" iconSize={16} type="button" variant="primary" onClick={() => setCreateOpen(true)}>Добавить сотрудника</Button></div>}
      />
      <EmployeesFilters groupId={groupId} groups={groups} query={query} role={role} resetFilters={resetFilters} setGroupId={(value) => { setGroupId(value); setMenuId(null); }} setQuery={(value) => { setQuery(value); setMenuId(null); }} setRole={(value) => { setRole(value); setMenuId(null); }} />
      <EmployeeTable employees={filtered} menuId={menuId} onTransfer={() => { setMenuId(null); setTransferOpen(true); }} openEmployee={openEmployee} setMenuId={setMenuId} total={employees.length} />
      <EmployeeCreateDrawer groups={groups} open={createOpen} onClose={() => setCreateOpen(false)} onCreated={() => { setCreateOpen(false); reload(); }} />
      <OwnershipTransferModal employees={employees} open={transferOpen} onClose={() => setTransferOpen(false)} />
    </>
  );
}
