import { useState } from "react";

import { FilterDropdown, SearchInput } from "../../shared/ui-controls";
import type { EmployeeGroup } from "../../types";
import { roleBadge, type EmployeeRoleFilter, type EmployeeStatusFilter } from "./model";
import { EmployeeFilterSelect } from "./EmployeeFilterSelect";
import { t } from "../../i18n";
import { statusLabel, workStatusCodes, type WorkStatusCode } from "../work-status/model";

// Фильтры списка сотрудников (кадры E1/E2): поиск · роль · группа · рабочий статус · «Сбросить».
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
  status,
  setStatus,
  workStatus,
  setWorkStatus,
}: {
  groupId: number | "all";
  groups: EmployeeGroup[];
  query: string;
  resetFilters: () => void;
  role: EmployeeRoleFilter;
  setGroupId: (groupId: number | "all") => void;
  setQuery: (query: string) => void;
  setRole: (role: EmployeeRoleFilter) => void;
  status: EmployeeStatusFilter;
  setStatus: (status: EmployeeStatusFilter) => void;
  workStatus: WorkStatusCode | "all";
  setWorkStatus: (status: WorkStatusCode | "all") => void;
}) {
  const [groupOpen, setGroupOpen] = useState(false);
  const [statusOpen, setStatusOpen] = useState(false);
  const dirty = query.trim() !== "" || role !== "all" || status !== "all" || groupId !== "all" || workStatus !== "all";
  const group = groups.find((item) => item.id === groupId) ?? null;
  return (
    <div className="employees-filters">
      <SearchInput className="employees-search" value={query} onChange={setQuery} hotkey="/" placeholder={t("admin.search_by_name_email_or")} />
      <EmployeeFilterSelect<EmployeeRoleFilter> label={t("common.role")} value={role} onChange={setRole}
        className="employees-role-filter" options={[
          { value: "all", label: t("common.all") },
          ...(["OWNER", "ADMIN", "SUPERVISOR", "EMPLOYEE"] as const).map(value => ({ value, label: roleBadge(value).text })),
        ]} />
      <EmployeeFilterSelect<EmployeeStatusFilter> label={t("employees.status")} value={status} onChange={setStatus}
        className="employees-status-filter" options={[
          { value: "all", label: t("common.all") },
          { value: "active", label: t("shared.active") },
          { value: "invited", label: t("shared.invited") },
          { value: "blocked", label: t("shared.blocked") },
          { value: "dismissed", label: t("employees.dismissed") },
        ]} />
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
      <div className="employees-filter-group">
        <span>{t("work_status.title")}</span>
        <FilterDropdown
          label={workStatus === "all" ? t("common.all") : statusLabel(workStatus)}
          open={statusOpen}
          options={[{ value: "all", label: t("common.all") }, ...workStatusCodes.map((code) => ({ value: code, label: statusLabel(code) }))]}
          selected={workStatus === "all" ? [] : [workStatus]}
          onOpenChange={setStatusOpen}
          onSelect={(value) => setWorkStatus(value as WorkStatusCode | "all")}
        />
      </div>
      <div className="employees-filters-spacer" />
      <button className={`employees-reset ${dirty ? "is-dirty" : ""}`} type="button" onClick={resetFilters}>{t("common.reset")}</button>
    </div>
  );
}
