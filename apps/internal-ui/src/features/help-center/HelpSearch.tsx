import { type FormEvent, useState } from "react";

import { HelpSearchIcon } from "./HelpIcons";

export function HelpSearch({
  value,
  onChange,
  onSubmit,
  compact = false,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit?: (value: string) => void;
  compact?: boolean;
}) {
  const [focused, setFocused] = useState(false);

  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit?.(value.trim());
  }

  return (
    <form
      className={`help-search ${compact ? "is-compact" : ""} ${focused ? "is-focused" : ""}`}
      role="search"
      onSubmit={submit}
    >
      <HelpSearchIcon />
      <input
        aria-label="Поиск по базе знаний"
        placeholder="Поиск по статьям..."
        type="search"
        value={value}
        onBlur={() => setFocused(false)}
        onChange={(event) => onChange(event.target.value)}
        onFocus={() => setFocused(true)}
      />
    </form>
  );
}
