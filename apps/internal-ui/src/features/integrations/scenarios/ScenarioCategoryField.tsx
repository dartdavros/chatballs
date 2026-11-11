import { useEffect, useState } from "react";
import { t } from "../../../i18n";
import { FormField } from "../../../shared/form-controls";
import { parseCategoryPath, validCategoryPath } from "./categoryPath";

type Props = { value: string[]; disabled: boolean; onChange: (value: string[]) => void };

export function ScenarioCategoryField({ value, disabled, onChange }: Props) {
  const [text, setText] = useState(() => value.join(" / "));
  const serialized = JSON.stringify(value);
  useEffect(() => {
    if (JSON.stringify(parseCategoryPath(text)) !== serialized) {
      setText((JSON.parse(serialized) as string[]).join(" / "));
    }
  }, [serialized, text]);

  return <div className="scenario-category-field">
    <FormField label={t("scenarios.category")} value={text} disabled={disabled}
      placeholder={t("scenarios.category_placeholder")}
      error={validCategoryPath(value) ? undefined : t("scenarios.category_invalid")}
      onChange={next => { setText(next); onChange(parseCategoryPath(next)); }} />
    <p className="scenario-note">{t("scenarios.category_hint")}</p>
  </div>;
}
