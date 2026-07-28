import { ContentLibraryToolbar } from "../../../shared/content-library/ContentLibraryToolbar";
import type { KnowledgeDepartmentReference, KnowledgeVisibility } from "./types";

type KnowledgeToolbarProps = {
  departments: KnowledgeDepartmentReference[];
  department?: number;
  isEnabled?: boolean;
  onDepartmentChange: (departmentId: number | undefined) => void;
  onEnabledChange: (isEnabled: boolean | undefined) => void;
  onQueryChange: (query: string) => void;
  onVisibilityChange: (visibility: KnowledgeVisibility | undefined) => void;
  query: string;
  visibility?: KnowledgeVisibility;
};

export function KnowledgeToolbar({
  departments,
  department,
  isEnabled,
  onDepartmentChange,
  onEnabledChange,
  query,
  onQueryChange,
  onVisibilityChange,
  visibility,
}: KnowledgeToolbarProps) {
  return (
    <ContentLibraryToolbar query={query} onQueryChange={onQueryChange}>
      <label className="knowledge-filter-select department">
        <span>Отдел:</span>
        <select value={department ?? ""} onChange={(event) => onDepartmentChange(event.target.value ? Number(event.target.value) : undefined)}>
          <option value="">Все</option>
          {departments.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}
        </select>
      </label>
      <label className="knowledge-filter-select visibility">
        <span>Доступность:</span>
        <select value={visibility ?? ""} onChange={(event) => onVisibilityChange(event.target.value ? event.target.value as KnowledgeVisibility : undefined)}>
          <option value="">Все</option>
          <option value="ORGANIZATION">Организация</option>
          <option value="DEPARTMENTS">Отделы</option>
        </select>
      </label>
      <label className="knowledge-filter-select status">
        <span>Статус:</span>
        <select value={isEnabled === undefined ? "" : String(isEnabled)} onChange={(event) => onEnabledChange(event.target.value === "" ? undefined : event.target.value === "true")}>
          <option value="">Все</option>
          <option value="true">Активно</option>
          <option value="false">Выключено</option>
        </select>
      </label>
    </ContentLibraryToolbar>
  );
}
