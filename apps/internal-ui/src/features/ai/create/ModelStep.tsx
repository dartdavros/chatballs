import { modelOptions } from "./model";
import { CreateAgentStepCard } from "./CreateAgentStepCard";

export function ModelStep({ model, setModel }: { model: string; setModel: (model: string) => void }) {
  return (
    <CreateAgentStepCard number={2} title="Базовая модель" text="Стартовая конфигурация создаётся из разрешённой модели. Позже модель и параметры меняются в карточке агента.">
      <div className="ai-create-field-offset">
        <select className="ai-create-model" value={model} onChange={(event) => setModel(event.target.value)}>
          {modelOptions.map((option) => <option value={option.value} key={option.value}>{option.label}</option>)}
        </select>
        <div className="ai-create-help">Список моделей задаётся в интеграции OpenRouter.</div>
      </div>
    </CreateAgentStepCard>
  );
}
