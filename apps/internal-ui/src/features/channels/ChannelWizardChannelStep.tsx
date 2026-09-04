import { FormField, SelectField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import type { EmployeeGroup } from "../../types";

export function ChannelWizardChannelStep({
  name,
  code,
  groupId,
  groups,
  onNameChange,
  onCodeChange,
  onGroupChange,
  onCancel,
  onNext,
}: {
  name: string;
  code: string;
  groupId: number | null;
  groups: EmployeeGroup[];
  onNameChange: (value: string) => void;
  onCodeChange: (value: string) => void;
  onGroupChange: (value: number | null) => void;
  onCancel: () => void;
  onNext: () => void;
}) {
  return (
    <section className="channel-card-section">
      <header><h3>Канал</h3></header>
      <div className="channel-wizard-fields">
        <FormField label="Название" value={name} onChange={onNameChange} placeholder="Партнёрская линия" />
        <FormField label="Код" value={code} mono placeholder="partners" onChange={onCodeChange} />
        <p className="channel-field-hint">Используется в адресе виджета и не меняется после создания.</p>
        <SelectField
          label="Группа"
          value={groupId === null ? "" : String(groupId)}
          onChange={(value) => onGroupChange(value ? Number(value) : null)}
          options={[["", "Без группы"], ...groups.map((item) => [String(item.id), item.name] as [string, string])]}
        />
        <p className="channel-field-hint">Группа определяет, какие сотрудники видят диалоги канала; без группы диалоги видны всем.</p>
      </div>
      <div className="channel-wizard-actions">
        <Button variant="secondary" onClick={onCancel}>Отмена</Button>
        <Button variant="primary" disabled={!name.trim() || !code} onClick={onNext}>Далее</Button>
      </div>
    </section>
  );
}
