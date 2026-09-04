import { PageHeader } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";

export function KnowledgePageHeader({
  canCreate,
  canImport,
  onCreate,
  onImport,
}: {
  canCreate: boolean;
  canImport: boolean;
  onCreate: () => void;
  onImport: () => void;
}) {
  return (
    <PageHeader
      title="Знания"
      text="Иерархическая библиотека знаний организации · категория задаёт размещение знания"
      action={(canImport || canCreate) && (
        <div className="knowledge-header-actions">
          {canImport && <Button variant="secondary" icon="download" onClick={onImport}>Импорт YAML</Button>}
          {canCreate && <Button variant="primary" icon="plus" onClick={onCreate}>Создать знание</Button>}
        </div>
      )}
    />
  );
}
