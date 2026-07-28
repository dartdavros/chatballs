import { Icon } from "../../../shared/icons";
import { ContentEditorCard } from "../../../shared/content-library/ContentEditorCard";
import { Button } from "../../../shared/ui-controls";
import { formatDate } from "../../../shared/utils";
import { KnowledgeEditorFields } from "./KnowledgeEditorFields";
import type { KnowledgeEditorState } from "./knowledgeEditorModel";
import type { KnowledgeCategory, KnowledgeDepartmentReference, KnowledgeItem } from "./types";

export function KnowledgeEditorCard({
  busy,
  categories,
  departments,
  editable,
  error,
  item,
  state,
  onChange,
  onDelete,
  onSave,
  onToggleEnabled,
}: {
  busy: boolean;
  categories: KnowledgeCategory[];
  departments: KnowledgeDepartmentReference[];
  editable: boolean;
  error: string | null;
  item: KnowledgeItem | null;
  state: KnowledgeEditorState;
  onChange: (state: KnowledgeEditorState) => void;
  onDelete?: () => void;
  onSave: () => void;
  onToggleEnabled?: () => void;
}) {
  return (
    <ContentEditorCard
      heading={<h3>Знание</h3>}
      meta={<><span className={`knowledge-card-status ${state.isEnabled ? "active" : "disabled"}`}><i />{state.isEnabled ? "Активно" : "Выключено"}</span>{item && <span className="knowledge-card-updated">обновлено {formatDate(item.updatedAt)}</span>}</>}
      error={error}
      actions={editable && <>
        <Button variant="primary" icon={item ? "save" : "plus"} disabled={busy} onClick={onSave}>
          {item ? "Сохранить" : "Создать знание"}
        </Button>
        {item && onToggleEnabled && (
          <Button variant="secondary" icon={state.isEnabled ? "eyeOff" : "eye"} disabled={busy} onClick={onToggleEnabled}>
            {state.isEnabled ? "Выключить" : "Включить"}
          </Button>
        )}
        <span />
        {item && onDelete && <Button className="knowledge-delete-button" variant="secondary" icon="trash" disabled={busy} onClick={onDelete}>Удалить</Button>}
      </>}
    >
      <KnowledgeEditorFields categories={categories} departments={departments} disabled={busy || !editable} state={state} onChange={onChange} />
    </ContentEditorCard>
  );
}
