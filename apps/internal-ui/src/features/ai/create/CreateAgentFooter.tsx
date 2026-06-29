import { Button } from "../../../shared/ui-controls";

export function CreateAgentFooter({ summary, ready, submitting, onCancel, onSubmit }: { summary: string; ready: boolean; submitting: boolean; onCancel: () => void; onSubmit: () => void }) {
  return (
    <div className="ai-create-footer">
      <div className="ai-create-footer-inner">
        <span>{summary}</span>
        <div>
          <Button variant="secondary" onClick={onCancel}>Отмена</Button>
          <Button variant="primary" icon="plus" disabled={!ready || submitting} onClick={onSubmit}>Создать агента</Button>
        </div>
      </div>
    </div>
  );
}
