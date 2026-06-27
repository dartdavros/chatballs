import { Icon } from "../../../shared/icons";
import { EmptyState } from "../../../shared/ui";
import { formatDate } from "../../../shared/utils";
import { knowledgeCategoryLabel, publishedVersion, type KnowledgeDoc } from "./model";

export function AiAgentKnowledgeTab({ knowledge, channelName }: { knowledge: KnowledgeDoc[]; channelName: string }) {
  if (knowledge.length === 0) {
    return <EmptyState title="Материалы знаний ещё не добавлены" />;
  }
  return (
    <section className="ai-card ai-card--flush">
      <div className="ai-knowledge-head">
        <h3>Обязательные знания release</h3>
        <div className="ai-knowledge-sub">Индекс поиска знаний · {channelName} · {knowledge.length} материалов</div>
      </div>
      {knowledge.map((doc) => {
        const version = publishedVersion(doc.versions);
        const meta = [knowledgeCategoryLabel(doc.category), version ? `v${version.version}` : null, `обновлено ${formatDate(doc.updatedAt)}`].filter(Boolean).join(" · ");
        return (
          <div className="ai-knowledge-row" key={doc.id}>
            <span className="ai-knowledge-icon"><Icon name="paperclip" size={16} /></span>
            <div className="ai-knowledge-info"><div className="ai-knowledge-title">{doc.title}</div><div className="ai-knowledge-meta">{meta}</div></div>
            <span className={doc.isEnabled ? "ai-knowledge-status on" : "ai-knowledge-status off"}>{doc.isEnabled ? "В индексе" : "Отключено"}</span>
          </div>
        );
      })}
    </section>
  );
}
