import { useEffect, type RefObject } from "react";

import { handleSearchShortcut } from "./searchShortcut";

const inputs = new Set<HTMLInputElement>();
const onKeyDown = (event: KeyboardEvent) => handleSearchShortcut(event, [...inputs]);

/** Один обработчик вместо конкурирующих shortcuts каждого смонтированного поля. */
export function useSearchShortcut(field: RefObject<HTMLInputElement | null>, hotkey = "/"): void {
  useEffect(() => {
    const input = field.current;
    if (!input || !hotkey) return;
    if (!inputs.size) window.addEventListener("keydown", onKeyDown);
    inputs.add(input);
    return () => {
      inputs.delete(input);
      if (!inputs.size) window.removeEventListener("keydown", onKeyDown);
    };
  }, [field, hotkey]);
}
