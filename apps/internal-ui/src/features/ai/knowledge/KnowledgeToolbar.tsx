import { PageHeader } from "../../../shared/ui";
import { Button, SearchInput } from "../../../shared/ui-controls";

type KnowledgeToolbarProps = {
  query: string;
  onQueryChange: (query: string) => void;
  onCreate: () => void;
  onImport: () => void;
};

export function KnowledgeToolbar({
  query,
  onQueryChange,
  onCreate,
  onImport,
}: KnowledgeToolbarProps) {
  return (
    <>
      <PageHeader
        title="Знания"
        text="Общая библиотека знаний · агент выбирает нужные знания в своей карточке"
        action={(
          <div className="knowledge-header-actions">
            <Button variant="secondary" icon="download" onClick={onImport}>Импорт YAML</Button>
            <Button variant="primary" icon="plus" onClick={onCreate}>Создать знание</Button>
          </div>
        )}
      />
      <div className="knowledge-toolbar">
        <SearchInput
          placeholder="Поиск по заголовку и описанию"
          value={query}
          onChange={onQueryChange}
        />
      </div>
    </>
  );
}
