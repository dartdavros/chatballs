import { Icon } from "../../../shared/icons";
import { CreateAgentStepCard } from "./CreateAgentStepCard";

const chips = ["Квалификация", "Поведение в продаже", "Ограничения"];

export function PromptStep({ systemPrompt, setSystemPrompt }: { systemPrompt: string; setSystemPrompt: (value: string) => void }) {
  return (
    <CreateAgentStepCard number={3} title="Стартовые инструкции" text="Создадим черновые prompt-документы. Доработать их можно в карточке агента до публикации.">
      <div className="ai-create-field-offset">
        <label className="ai-create-label">Системный prompt</label>
        <textarea value={systemPrompt} onChange={(event) => setSystemPrompt(event.target.value)} rows={4} />
        <div className="ai-create-chips">
          {chips.map((chip) => <span key={chip}><Icon name="check" size={12} />{chip}</span>)}
          <small>— будут созданы как черновики</small>
        </div>
      </div>
    </CreateAgentStepCard>
  );
}
