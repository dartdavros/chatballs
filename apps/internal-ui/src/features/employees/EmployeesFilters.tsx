import { Button, SearchInput } from "../../shared/ui-controls";
import type { EmployeeGroup } from "../../types";
import { roleBadge, type EmployeeRoleFilter, type EmployeeStatusFilter } from "./model";
import { EmployeeFilterSelect } from "./EmployeeFilterSelect";
import { t } from "../../i18n";
import { statusLabel, workStatusCodes, type WorkStatusCode } from "../work-status/model";

// Фильтры списка сотрудников (кадры E1/E2): поиск · роль · группа · рабочий статус · «Сбросить».

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
  return (
    <div className="employees-filters">
      <SearchInput className="employees-search" value={query} onChange={setQuery} hotkey="/" placeholder={t("admin.search_by_name_email_or")} />
      <EmployeeFilterSelect<EmployeeRoleFilter> caption={t("common.role")} value={role} onChange={setRole}
        options={[
          { value: "all", label: t("common.all") },
          ...(["OWNER", "ADMIN", "SUPERVISOR", "EMPLOYEE"] as const).map(value => ({ value, label: roleBadge(value).text })),
        ]} />
      <EmployeeFilterSelect<EmployeeStatusFilter> caption={t("employees.status")} value={status} onChange={setStatus}
        options={[
          { value: "all", label: t("common.all") },
          { value: "active", label: t("shared.active") },
          { value: "invited", label: t("shared.invited") },
          { value: "blocked", label: t("shared.blocked") },
          { value: "dismissed", label: t("employees.dismissed") },
        ]} />
      {groups.length > 0 && (
        <EmployeeFilterSelect caption={t("common.group")} value={String(groupId)}
          options={[{ value: "all", label: t("common.all") }, ...groups.map((item) => ({ value: String(item.id), label: item.name }))]}
          onChange={(value) => setGroupId(value === "all" ? "all" : Number(value))} />
      )}
      <EmployeeFilterSelect<WorkStatusCode | "all"> caption={t("work_status.title")} value={workStatus}
        options={[{ value: "all", label: t("common.all") }, ...workStatusCodes.map((code) => ({ value: code, label: statusLabel(code) }))]}
        onChange={setWorkStatus} />
      <Button variant="secondary" onClick={resetFilters}>{t("common.reset")}</Button>
    </div>
  );
}
