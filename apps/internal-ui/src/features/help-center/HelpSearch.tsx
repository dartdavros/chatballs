import { type FormEvent, useState } from "react";

import { HelpSearchIcon } from "./HelpIcons";
import { t } from "../../i18n";

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
        aria-label={t("portals.search_knowledge_base")}
        placeholder={t("portals.search_articles_2")}
        type="search"
        value={value}
        onBlur={() => setFocused(false)}
        onChange={(event) => onChange(event.target.value)}
        onFocus={() => setFocused(true)}
      />
    </form>
  );
}
