import { useState } from "react";
import { t } from "../../i18n";
import { FilterDropdown } from "../../shared/ui-controls";

export function EmployeeFilterSelect<T extends string>({ caption, value, options, onChange }: {
  caption: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <FilterDropdown caption={`${caption}:`} label={options.find(item => item.value === value)?.label ?? t("common.all")}
      open={open} onOpenChange={setOpen} options={options} selected={value === "all" ? [] : [value]}
      onSelect={next => onChange(next as T)} />
  );
}
