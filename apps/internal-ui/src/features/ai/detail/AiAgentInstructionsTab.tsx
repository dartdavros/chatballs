import { Icon } from "../../../shared/icons";
import { EmptyState } from "../../../shared/ui";
import { promptCategoryLabel, publishedVersion, type PromptDoc } from "./model";

export function AiAgentInstructionsTab({ prompts }: { prompts: PromptDoc[] }) {
  if (prompts.length === 0) {
    return <EmptyState title="Промпты ещё не заданы" />;
  }
  return (
    <div className="ai-instructions">
      <div className="ai-notice">
        <Icon name="warning" size={17} />
        <span>Инструкции редактируются в составе черновика версии. Опубликованная версия доступна только для чтения — изменения применяются после публикации новой версии.</span>
      </div>
      {prompts.map((prompt, index) => {
        const version = publishedVersion(prompt.versions);
        return (
          <section className="ai-card" key={prompt.id}>
            <div className="ai-instruction-head">
              <span className="ai-instruction-index">{index + 1}</span>
              <h3>{prompt.title}</h3>
              <small>{promptCategoryLabel(prompt.category)}</small>
            </div>
            <pre className="ai-prompt-block">{version?.content?.trim() || "—"}</pre>
          </section>
        );
      })}
    </div>
  );
}
