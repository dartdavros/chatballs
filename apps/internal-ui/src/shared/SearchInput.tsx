import { useRef, type RefObject } from "react";

import { t } from "../i18n";
import { Icon } from "./icons";
import { useSearchShortcut } from "./useSearchShortcut";
import "./search-input.css";

type SearchInputProps = {
  clearable?: boolean;
  className?: string;
  disabled?: boolean;
  hotkey?: string;
  id?: string;
  inputRef?: RefObject<HTMLInputElement | null>;
  label?: string;
  onChange?: (value: string) => void;
  placeholder: string;
  value?: string;
};

/** Общая подсказка поиска, в том числе для публичного портала. */
export function SearchShortcut({ hotkey = "/" }: { hotkey?: string }) {
  return <kbd className="ui-search-shortcut" aria-hidden="true">{hotkey}</kbd>;
}

/** Поиск списка: та же клавиша и её подсказка во всех списках и окнах. */
export function SearchInput({ className = "", placeholder, value, onChange, inputRef, hotkey = "/", clearable, disabled, id, label }: SearchInputProps) {
  const ownRef = useRef<HTMLInputElement | null>(null);
  const field = inputRef ?? ownRef;
  useSearchShortcut(field, hotkey);

  return (
    <label className={`ui-search-input ${className}`.trim()}>
      <Icon name="search" size={15} />
      <input ref={field} id={id} disabled={disabled} aria-label={label ?? placeholder} aria-keyshortcuts={disabled ? undefined : hotkey || undefined}
        value={value} onChange={(event) => onChange?.(event.target.value)} placeholder={placeholder} />
      {clearable && value && <button className="ui-search-clear" type="button" disabled={disabled} aria-label={t("shared.clear_search")}
        onClick={() => { onChange?.(""); field.current?.focus(); }}><Icon name="close" size={13} /></button>}
      {!disabled && hotkey && !value && <SearchShortcut hotkey={hotkey} />}
    </label>
  );
}
