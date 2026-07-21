import { FormField, SelectField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import type { Department } from "../../types";

export function ChannelWizardChannelStep({
  name,
  code,
  departmentId,
  departments,
  onNameChange,
  onCodeChange,
  onDepartmentChange,
  onCancel,
  onNext,
}: {
  name: string;
  code: string;
  departmentId: number | null;
  departments: Department[];
  onNameChange: (value: string) => void;
  onCodeChange: (value: string) => void;
  onDepartmentChange: (value: number | null) => void;
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
          label="Отдел"
          value={departmentId === null ? "" : String(departmentId)}
          onChange={(value) => onDepartmentChange(value ? Number(value) : null)}
          options={[["", "Без отдела"], ...departments.map((item) => [String(item.id), item.name] as [string, string])]}
        />
      </div>
      <div className="channel-wizard-actions">
        <Button variant="secondary" onClick={onCancel}>Отмена</Button>
        <Button variant="primary" disabled={!name.trim() || !code} onClick={onNext}>Далее</Button>
      </div>
    </section>
  );
}
