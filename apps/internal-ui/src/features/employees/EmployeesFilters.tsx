import type { Role } from "../../types";
import { SearchInput } from "../../shared/ui-controls";
import { Segmented } from "../../shared/ui";
import type { EmployeeStatusFilter } from "./model";

export function EmployeesFilters({
  query,
  role,
  status,
  resetFilters,
  setQuery,
  setRole,
  setStatus,
}: {
  query: string;
  role: "all" | Role;
  status: EmployeeStatusFilter;
  resetFilters: () => void;
  setQuery: (query: string) => void;
  setRole: (role: "all" | Role) => void;
  setStatus: (status: EmployeeStatusFilter) => void;
}) {
  return (
    <div className="filter-bar employees-filter">
      <SearchInput className="employee-search" value={query} onChange={setQuery} placeholder="Поиск по имени или email…" />
      <div className="filter-group">
        <span>Роль</span>
        <Segmented value={role} setValue={setRole} items={[["all", "Все"], ["OWNER", "OWNER"], ["OPERATOR", "OPERATOR"]]} />
      </div>
      <div className="filter-group">
        <span>Статус</span>
        <Segmented value={status} setValue={setStatus} items={[["all", "Все"], ["active", "Активные"], ["invited", "Приглашённые"], ["blocked", "Заблокированные"]]} />
      </div>
      <button className="reset-filter" type="button" onClick={resetFilters}>Сбросить</button>
    </div>
  );
}
