import { EmptyState } from "../../../shared/ui";
import { DocCard } from "./DocCard";
import { DocCreateForm } from "./DocCreateForm";
import { knowledgeCategoryLabel, knowledgeCategoryOptions, type KnowledgeDoc } from "./model";

export function AiAgentKnowledgeTab({ knowledge, channelName, product, onChanged }: { knowledge: KnowledgeDoc[]; channelName: string; product: { code: string; name: string } | null; onChanged: () => void }) {
  return (
    <div className="ai-instructions">
      <div className="ai-knowledge-headline">База знаний · {channelName} · {knowledge.length} материалов</div>
      {knowledge.length === 0 && <EmptyState title="Материалы знаний ещё не добавлены" />}
      {knowledge.map((doc, index) => (
        <DocCard
          key={doc.id}
          kind="knowledge"
          index={index + 1}
          id={doc.id}
          title={doc.title}
          category={knowledgeCategoryLabel(doc.category)}
          isEnabled={doc.isEnabled}
          versions={doc.versions}
          meta={
            <>
              <span className={`ai-doc-chip ${doc.scope === "GLOBAL" ? "scope-global" : "scope-product"}`}>
                {doc.scope === "GLOBAL" ? "Глобально" : doc.product?.name ?? "Продукт"}
              </span>
              <span className="ai-doc-chip plain">{doc.inclusionMode === "MANDATORY" ? "Всегда в контексте" : "Поиск"}</span>
            </>
          }
          onChanged={onChanged}
        />
      ))}
      <DocCreateForm kind="knowledge" categories={knowledgeCategoryOptions} product={product} withInclusion onCreated={onChanged} />
    </div>
  );
}
