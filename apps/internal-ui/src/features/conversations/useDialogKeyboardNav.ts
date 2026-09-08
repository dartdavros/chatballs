import { useEffect, useRef } from "react";

import type { ConversationListItem } from "./types";

/** Клавиатура списка диалогов (SPEC-CHATBALLS-0031 §9): ↑/↓ — по списку,
 *  Enter — открыть диалог на мобильном. «/» держит сам SearchInput. */
export function useDialogKeyboardNav({
  dialogs,
  selectedId,
  setSelectedId,
  onOpen,
}: {
  dialogs: ConversationListItem[];
  selectedId: number | null;
  setSelectedId: (id: number) => void;
  onOpen: () => void;
}): void {
  const dialogsRef = useRef(dialogs);
  dialogsRef.current = dialogs;
  const selectedRef = useRef(selectedId);
  selectedRef.current = selectedId;
  const setSelectedRef = useRef(setSelectedId);
  setSelectedRef.current = setSelectedId;
  const onOpenRef = useRef(onOpen);
  onOpenRef.current = onOpen;

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target?.closest("input, textarea, [contenteditable], .ant-dropdown")) return;
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        const list = dialogsRef.current;
        if (!list.length) return;
        event.preventDefault();
        const index = list.findIndex((dialog) => dialog.id === selectedRef.current);
        const next = event.key === "ArrowDown"
          ? list[Math.min(index + 1, list.length - 1)]
          : list[Math.max(index - 1, 0)];
        if (next) setSelectedRef.current(next.id);
        return;
      }
      if (event.key === "Enter" && selectedRef.current != null) onOpenRef.current();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);
}
