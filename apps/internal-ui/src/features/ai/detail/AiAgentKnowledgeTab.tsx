import { Icon } from "../../../shared/icons";
import { EmptyState } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import type { RouteKey } from "../../../types";
import type { AiAgentDetail } from "./model";

/**
 * Список знаний агента — только чтение. Состав меняется массовыми действиями в
 * разделах «Знания» и «Поддержка»: один способ управления вместо двух.
 */
export function AiAgentKnowledgeTab({ agent, openKnowledge, setRoute }: { agent: AiAgentDetail; openKnowledge: (knowledgeId: number) => void; setRoute: (route: RouteKey) => void }) {
  const total = agent.knowledge.length + agent.portalArticles.length;

  return (
    <div className="ai-instructions">
      <div className="ai-knowledge-headline">
        <span>Знания агента · {agent.channel.name} · всего {total}</span>
        <Button variant="secondary" icon="external" onClick={() => setRoute("aiKnowledge")}>Перейти в знания</Button>
      </div>
      {total === 0 && (
        <EmptyState title="Знания не прикреплены — выберите их в разделе «Знания» или статьи на портале поддержки" />
      )}
      {agent.knowledge.length > 0 && (
        <section className="ai-card">
          <h4 className="agent-knowledge-group">Знания библиотеки</h4>
          <ul className="agent-knowledge-list is-readonly">
            {agent.knowledge.map((item) => (
              <li key={item.id}>
                <button className="link is-strong is-neutral agent-knowledge-text" type="button" onClick={() => openKnowledge(item.id)}>
                  {item.title}
                </button>
                {!item.isEnabled && <span className="ai-doc-chip off">Выключено</span>}
                <button type="button" className="row-menu-button" aria-label={`Открыть знание ${item.title}`} onClick={() => openKnowledge(item.id)}><Icon name="external" size={15} /></button>
              </li>
            ))}
          </ul>
        </section>
      )}
      {agent.portalArticles.length > 0 && (
        <section className="ai-card">
          <h4 className="agent-knowledge-group">Статьи поддержки</h4>
          <ul className="agent-knowledge-list is-readonly">
            {agent.portalArticles.map((article) => (
              <li key={article.id}>
                <a className="link is-strong is-neutral agent-knowledge-text" href={article.publicUrl} rel="noreferrer" target="_blank">
                  {article.title}
                </a>
                <span className="ai-doc-chip plain">{article.portal.name}</span>
                {article.status !== "PUBLISHED" && <span className="ai-doc-chip off">{article.status === "ARCHIVED" ? "Архив" : "Черновик"}</span>}
                <a className="row-menu-button" aria-label={`Открыть статью ${article.title}`} href={article.publicUrl} rel="noreferrer" target="_blank"><Icon name="external" size={15} /></a>
              </li>
            ))}
          </ul>
        </section>
      )}
      {total > 0 && (
        <p className="ai-doc-updated">Агент использует только включённые знания и опубликованные статьи.</p>
      )}
    </div>
  );
}
