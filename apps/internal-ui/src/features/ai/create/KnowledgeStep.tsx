import { Icon } from "../../../shared/icons";
import { LoadingState } from "../../../shared/ui";
import type { KnowledgeItem } from "../knowledge/model";
import { CreateAgentStepCard } from "./CreateAgentStepCard";

export function KnowledgeStep({ items, selectedIds, loading, toggle }: { items: KnowledgeItem[]; selectedIds: number[]; loading: boolean; toggle: (id: number) => void }) {
  return (
    <CreateAgentStepCard number={4} title="Знания агента" text="Выберите знания из общей библиотеки. Изменить выбор можно в карточке агента в любой момент.">
      <div className="ai-create-field-offset ai-create-knowledge">
        {loading ? (
          <LoadingState variant="inline" />
        ) : (
          items.map((item) => {
            const selected = selectedIds.includes(item.id);
            return (
              <button className={selected ? "is-selected" : ""} type="button" onClick={() => toggle(item.id)} key={item.id}>
                <span>{selected && <Icon name="check" size={12} />}</span>
                <strong>{item.title}</strong>
                <small>{item.description || (item.attachments.length > 0 ? `${item.attachments.length} влож.` : "")}</small>
              </button>
            );
          })
        )}
      </div>
    </CreateAgentStepCard>
  );
}
