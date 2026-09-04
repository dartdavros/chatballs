import { ContentLibraryToolbar } from "../../../shared/content-library/ContentLibraryToolbar";

type KnowledgeToolbarProps = {
  isEnabled?: boolean;
  onEnabledChange: (isEnabled: boolean | undefined) => void;
  onQueryChange: (query: string) => void;
  query: string;
};

export function KnowledgeToolbar({
  isEnabled,
  onEnabledChange,
  query,
  onQueryChange,
}: KnowledgeToolbarProps) {
  return (
    <ContentLibraryToolbar query={query} onQueryChange={onQueryChange}>
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
