import { Icon } from "../../../shared/icons";
import { LoadingState } from "../../../shared/ui";
import { knowledgeMeta, type KnowledgeDocument } from "./model";
import { CreateAgentStepCard } from "./CreateAgentStepCard";

export function KnowledgeStep({ documents, selectedIds, loading, toggle }: { documents: KnowledgeDocument[]; selectedIds: number[]; loading: boolean; toggle: (id: number) => void }) {
  return (
    <CreateAgentStepCard number={4} title="Обязательные знания" text="Выберите материалы из базы знаний продукта. Они войдут в retrieval index первой версии.">
      <div className="ai-create-field-offset ai-create-knowledge">
        {loading ? (
          <LoadingState variant="inline" />
        ) : (
          documents.map((document) => {
            const selected = selectedIds.includes(document.id);
            return (
              <button className={selected ? "is-selected" : ""} type="button" onClick={() => toggle(document.id)} key={document.id}>
                <span>{selected && <Icon name="check" size={12} />}</span>
                <strong>{document.title}</strong>
                <small>{knowledgeMeta(document)}</small>
              </button>
            );
          })
        )}
        <button className="ai-create-knowledge-new" type="button"><Icon name="plus" size={14} />Создать новый материал знаний</button>
      </div>
    </CreateAgentStepCard>
  );
}
