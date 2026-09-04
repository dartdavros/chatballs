import { Segmented } from "../../shared/ui";
import { SearchInput } from "../../shared/ui-controls";
import type { EmployeeGroup } from "../../types";
import type { EmployeeRoleFilter } from "./model";

export function EmployeesFilters({
  groupId,
  groups,
  query,
  resetFilters,
  role,
  setGroupId,
  setQuery,
  setRole,
}: {
  groupId: number | "all";
  groups: EmployeeGroup[];
  query: string;
  resetFilters: () => void;
  role: EmployeeRoleFilter;
  setGroupId: (groupId: number | "all") => void;
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
      {groups.length > 0 && (
        <div className="filter-group">
          <span>Группа</span>
          <select value={String(groupId)} onChange={(event) => setGroupId(event.target.value === "all" ? "all" : Number(event.target.value))}>
            <option value="all">Все</option>
            {groups.map((group) => <option value={group.id} key={group.id}>{group.name}</option>)}
          </select>
        </div>
      )}
      <button className="reset-filter" type="button" onClick={resetFilters}>Сбросить</button>
    </div>
  );
}
