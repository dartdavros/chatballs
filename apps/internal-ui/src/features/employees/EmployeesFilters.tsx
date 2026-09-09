import { useState } from "react";

import { Segmented } from "../../shared/ui";
import { FilterDropdown, SearchInput } from "../../shared/ui-controls";
import type { EmployeeGroup } from "../../types";
import type { EmployeeRoleFilter } from "./model";
import { t } from "../../i18n";

// Фильтры списка сотрудников (кадры E1/E2): поиск · роль · группа · «Сбросить».
// «Сбросить» подсвечивается акцентом, когда фильтры отличаются от исходных.

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
  const [groupOpen, setGroupOpen] = useState(false);
  const dirty = query.trim() !== "" || role !== "all" || groupId !== "all";
  const group = groups.find((item) => item.id === groupId) ?? null;
  return (
    <div className="employees-filters">
      <SearchInput className="employees-search" value={query} onChange={setQuery} hotkey="/" placeholder={t("admin.search_by_name_email_or")} />
      <div className="employees-filter-group">
        <span>{t("common.role")}</span>
        <Segmented value={role} setValue={setRole} items={[["all", t("common.all")], ["OWNER", t("common.owner")], ["ADMIN", t("common.administrator")], ["EMPLOYEE", t("common.operator")]]} />
      </div>
      {groups.length > 0 && (
        <div className="employees-filter-group">
          <span>{t("common.group")}</span>
          <FilterDropdown
            className="employees-group-filter"
            label={group ? group.name : t("common.all")}
            open={groupOpen}
            options={[{ value: "all", label: t("common.all") }, ...groups.map((item) => ({ value: String(item.id), label: item.name }))]}
            selected={groupId === "all" ? [] : [String(groupId)]}
            onOpenChange={setGroupOpen}
            onSelect={(value) => setGroupId(value === "all" ? "all" : Number(value))}
          />
        </div>
      )}
      <div className="employees-filters-spacer" />
      <button className={`employees-reset ${dirty ? "is-dirty" : ""}`} type="button" onClick={resetFilters}>{t("common.reset")}</button>
    </div>
  );
}
