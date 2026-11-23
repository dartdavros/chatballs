import { useState } from "react";
import { FilterDropdown } from "../../shared/ui-controls";

export function EmployeeFilterSelect<T extends string>({ label, value, options, onChange, className }: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
  className: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="employees-filter-group">
      <span>{label}</span>
      <FilterDropdown className={className} label={options.find(item => item.value === value)?.label ?? ""}
        open={open} onOpenChange={setOpen} options={options} selected={value === "all" ? [] : [value]}
        onSelect={next => onChange(next as T)} />
    </div>
  );
}
