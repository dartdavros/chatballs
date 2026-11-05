import { useEffect, useState, type ReactNode } from "react";
import { t } from "../../../../i18n";
import { FormField } from "../../../../shared/form-controls";

export function StructuredObjectEntry({ name, names, disabled, rename, remove, children }: {
  name: string; names: string[]; disabled: boolean; rename: (name: string) => void;
  remove: () => void; children: ReactNode;
}) {
  const [draft, setDraft] = useState(name);
  useEffect(() => setDraft(name), [name]);
  const duplicate = draft !== name && names.includes(draft);
  return <div className="scenario-bound-children">
    <FormField label={t("skill_templates.field_name")} value={draft} disabled={disabled} wide
      onChange={setDraft} onBlur={() => { if (!duplicate) rename(draft); }}
      error={duplicate ? t("skill_templates.duplicate") : undefined} />
    {children}
    <button type="button" className="link" disabled={disabled} onClick={remove}>{t("scenarios.remove")}</button>
  </div>;
}

