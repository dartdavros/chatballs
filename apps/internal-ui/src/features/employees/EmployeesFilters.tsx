import { Segmented } from "../../shared/ui";
import { SearchInput } from "../../shared/ui-controls";
import type { EmployeePlacementFilter, EmployeeRoleFilter } from "./model";

export function EmployeesFilters({
  placement,
  query,
  resetFilters,
  role,
  setPlacement,
  setQuery,
  setRole,
}: {
  placement: EmployeePlacementFilter;
  query: string;
  resetFilters: () => void;
  role: EmployeeRoleFilter;
  setPlacement: (placement: EmployeePlacementFilter) => void;
  setQuery: (query: string) => void;
  setRole: (role: EmployeeRoleFilter) => void;
}) {
  return (
    <div className="filter-bar employees-filter">
      <SearchInput className="employee-search" value={query} onChange={setQuery} placeholder="Поиск по имени, email, должности…" />
      <div className="filter-group">
        <span>Роль</span>
        <Segmented value={role} setValue={setRole} items={[["all", "Все"], ["OWNER", "Владелец"], ["ADMIN", "Администратор"], ["EMPLOYEE", "Сотрудник"]]} />
      </div>
      <div className="filter-group">
        <span>Размещение</span>
        <Segmented value={placement} setValue={setPlacement} items={[["all", "Все"], ["company", "Компания"], ["department", "Отдел"]]} />
      </div>
      <button className="reset-filter" type="button" onClick={resetFilters}>Сбросить</button>
    </div>
  );
}
