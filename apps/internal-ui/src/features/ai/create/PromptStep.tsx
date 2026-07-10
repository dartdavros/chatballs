import { CreateAgentStepCard } from "./CreateAgentStepCard";

export function PromptStep({ persona, tone, instructions, setPersona, setTone, setInstructions }: { persona: string; tone: string; instructions: string; setPersona: (value: string) => void; setTone: (value: string) => void; setInstructions: (value: string) => void }) {
  return (
    <CreateAgentStepCard number={3} title="Инструкции агента" text="Три части инструкций: кто он, как говорит и по каким правилам работает. Доработать можно в карточке агента.">
      <div className="ai-create-field-offset">
        <label className="ai-create-label">Персонализация — кто он и что он</label>
        <textarea value={persona} onChange={(event) => setPersona(event.target.value)} rows={3} />
        <label className="ai-create-label">Тон общения — как он должен говорить</label>
        <textarea value={tone} onChange={(event) => setTone(event.target.value)} rows={3} />
        <label className="ai-create-label">Инструкции — правила работы</label>
        <textarea value={instructions} onChange={(event) => setInstructions(event.target.value)} rows={4} />
      </div>
    </CreateAgentStepCard>
  );
}
