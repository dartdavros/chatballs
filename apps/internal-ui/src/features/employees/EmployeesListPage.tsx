import { useState } from "react";

import { hasCapability } from "../../auth/access";
import { PageHeader } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import type { Department, Employee, RouteKey, SessionUser } from "../../types";
import { useAccessCatalog } from "./access-api";
import { EmployeeCreateDrawer } from "./EmployeeCreateDrawer";
import { EmployeeTable } from "./EmployeeTable";
import { EmployeesFilters } from "./EmployeesFilters";
import { filterEmployees, type EmployeePlacementFilter, type EmployeeRoleFilter } from "./model";
import { OwnershipTransferModal } from "./OwnershipTransferModal";

export function EmployeesPage({ departments, employees, reload, openEmployee, setRoute, user }: {
  departments: Department[];
  employees: Employee[];
  reload: () => void;
  openEmployee: (employee: Employee) => void;
  setRoute: (route: RouteKey) => void;
  user: SessionUser;
}) {
  const [role, setRole] = useState<EmployeeRoleFilter>("all");
  const [placement, setPlacement] = useState<EmployeePlacementFilter>("all");
  const [query, setQuery] = useState("");
  const [menuId, setMenuId] = useState<number | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [transferOpen, setTransferOpen] = useState(false);
  const canManage = hasCapability(user, "employees.manage");
  const access = useAccessCatalog(canManage);
  const filtered = filterEmployees(employees, role, placement, query);

  function resetFilters() {
    setQuery(""); setRole("all"); setPlacement("all"); setMenuId(null);
  }

  return (
    <>
      <PageHeader
        title="Сотрудники"
        text={<>Системные роли, должности и размещение · показано <b>{filtered.length}</b> из {employees.length}</>}
        action={canManage && <div className="employee-page-actions"><Button icon="columns" iconSize={16} type="button" variant="secondary" onClick={() => setRoute("accessProfiles")}>Профили доступа</Button><Button icon="team" iconSize={16} type="button" variant="primary" onClick={() => setCreateOpen(true)}>Добавить сотрудника</Button></div>}
      />
      <EmployeesFilters placement={placement} query={query} role={role} resetFilters={resetFilters} setPlacement={(value) => { setPlacement(value); setMenuId(null); }} setQuery={(value) => { setQuery(value); setMenuId(null); }} setRole={(value) => { setRole(value); setMenuId(null); }} />
      <EmployeeTable departments={departments} employees={filtered} menuId={menuId} onTransfer={() => { setMenuId(null); setTransferOpen(true); }} openEmployee={openEmployee} setMenuId={setMenuId} total={employees.length} />
      <EmployeeCreateDrawer departments={departments} open={createOpen} profiles={access.profiles} user={user} onClose={() => setCreateOpen(false)} onCreated={() => { setCreateOpen(false); reload(); }} />
      <OwnershipTransferModal employees={employees} open={transferOpen} onClose={() => setTransferOpen(false)} />
    </>
  );
}
