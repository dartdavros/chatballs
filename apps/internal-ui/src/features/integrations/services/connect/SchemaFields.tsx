import type { ServiceField } from "../types";
import { fieldControl, type ServiceValues } from "./fieldControls";

// Поля доступа рисуются по схеме адаптера и ключу контрола из общего реестра
// (backend adapters/controls.py). Названия сервисов экран не знает.

type Props = {
  fields: ServiceField[];
  values: ServiceValues;
  errors: Record<string, string>;
  disabled: boolean;
  onChange: (name: string, value: unknown) => void;
};

export function SchemaFields({ fields, values, errors, disabled, onChange }: Props) {
  return (
    <>
      {fields.map((field) => {
        const Control = fieldControl(field);
        return Control && (
        <div className="service-field" key={field.name}>
          <Control field={field} value={values[field.name]} error={errors[field.name]} disabled={disabled}
            onChange={(value) => onChange(field.name, value)} />
          {field.hint && <small>{field.hint}</small>}
        </div>
      ); })}
    </>
  );
}
