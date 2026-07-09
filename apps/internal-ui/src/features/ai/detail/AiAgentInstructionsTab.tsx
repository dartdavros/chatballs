import { EmptyState } from "../../../shared/ui";
import { DocCard } from "./DocCard";
import { DocCreateForm } from "./DocCreateForm";
import { DocImportForm } from "./DocImportForm";
import { promptCategoryLabel, promptCategoryOptions, type PromptDoc } from "./model";

export function AiAgentInstructionsTab({ prompts, product, onChanged }: { prompts: PromptDoc[]; product: { code: string; name: string } | null; onChanged: () => void }) {
  return (
    <div className="ai-instructions">
      {prompts.length === 0 && <EmptyState title="Промпты ещё не заданы" />}
      {prompts.map((prompt, index) => (
        <DocCard
          key={prompt.id}
          kind="prompts"
          index={index + 1}
          id={prompt.id}
          title={prompt.title}
          category={promptCategoryLabel(prompt.category)}
          isEnabled={prompt.isEnabled}
          versions={prompt.versions}
          onChanged={onChanged}
        />
      ))}
      <DocCreateForm kind="prompts" categories={promptCategoryOptions} product={product} onCreated={onChanged} />
      <DocImportForm kind="prompts" onImported={onChanged} />
    </div>
  );
}
