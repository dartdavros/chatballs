import { useCallback, useMemo, useState } from "react";

import { hasCapability } from "../../auth/access";
import { Icon } from "../../shared/icons";
import { Pagination } from "../../shared/Pagination";
import { Button } from "../../shared/ui-controls";
import { useDebounced } from "../../shared/useDebounced";
import { usePagedResource } from "../../shared/usePagedResource";
import type { Employee, EmployeeGroup, RouteKey, SessionUser } from "../../types";
import { EmployeeCreateDrawer } from "./EmployeeCreateDrawer";
import { EmployeePasswordDialog } from "./EmployeePasswordDialog";
import { EmployeeTable } from "./EmployeeTable";
import { EmployeesFilters } from "./EmployeesFilters";
import { blockEmployee, fetchEmployees, resetEmployeePassword, terminateEmployeeSessions, type IssuedPassword } from "./api";
import type { EmployeeRoleFilter } from "./model";

// Список сотрудников (дизайн-базлайн v2, «Сотрудники Baseline», кадры E1/E2).
// Страницу, фильтры и поиск считает сервер: список растёт вместе с компанией.

export function EmployeesPage({ groups, openEmployee, user }: {
  groups: EmployeeGroup[];
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
  // Поиск придерживается: запрос уходит, когда человек перестал печатать.
  const settledQuery = useDebounced(query);
  const filters = useMemo(
    () => ({ role, groupId, query: settledQuery }),
    [groupId, role, settledQuery],
  );
  const load = useCallback((page: number) => fetchEmployees(filters, page), [filters]);
  const employees = usePagedResource(load, filters, "Не удалось загрузить сотрудников");

  function resetFilters() {
    setQuery(""); setRole("all"); setGroupId("all"); setMenuId(null);
  }

  async function run(action: () => Promise<void>) {
    setError("");
    try {
      await action();
      await employees.reload();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось выполнить действие");
    }
  }

  return (
    <div className="employees-page">
      <header className="employees-header">
        <div>
          <h2>Сотрудники</h2>
          <p>Роли и группы · показано <b>{employees.items.length}</b> из {employees.total}</p>
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

      {(error || employees.errorText) && <div className="employees-error"><Icon name="alert" size={16} strokeWidth={1.8} />{error || employees.errorText}</div>}

      <EmployeeTable
        employees={employees.items}
        groups={groups}
        menuId={menuId}
        onBlock={(employee) => void run(() => blockEmployee(employee.id, !employee.isBlocked))}
        onResetPassword={(employee) => void run(async () => { setIssued(await resetEmployeePassword(employee.id, "show")); })}
        onTerminateSessions={(employee) => void run(() => terminateEmployeeSessions(employee.id))}
        openEmployee={openEmployee}
        setMenuId={setMenuId}
        total={employees.total}
      />
      {employees.pageCount > 1 && (
        <Pagination
          className="employees-pagination"
          note={`Показано ${employees.items.length} из ${employees.total}`}
          page={employees.page}
          pageCount={employees.pageCount}
          onPage={employees.setPage}
        />
      )}

      {createOpen && (
        <EmployeeCreateDrawer
          groups={groups}
          onClose={() => setCreateOpen(false)}
          onCreated={(password) => { setCreateOpen(false); void employees.reload(); if (password) setIssued(password); }}
        />
      )}
      {issued && <EmployeePasswordDialog issued={issued} onClose={() => setIssued(null)} />}
    </div>
  );
}
