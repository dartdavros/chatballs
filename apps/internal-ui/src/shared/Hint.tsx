import { useState, type ReactNode } from "react";

import { Icon } from "./icons";

// Реестр inline-подсказок первого визита (дизайн-базлайн v2, кадр A1; §6 —
// сотрудникам подсказки не показываются, это решает вызывающая сторона).
// Закрытие запоминается на устройстве по ключу `id`.

const STORAGE_PREFIX = "chatbolls.hint.";

function isDismissed(id: string): boolean {
  try {
    return window.localStorage.getItem(STORAGE_PREFIX + id) === "dismissed";
  } catch {
    return false;
  }
}

export function Hint({ id, children }: { id: string; children: ReactNode }) {
  const [dismissed, setDismissed] = useState(() => isDismissed(id));
  if (dismissed) return null;

  function dismiss() {
    setDismissed(true);
    try {
      window.localStorage.setItem(STORAGE_PREFIX + id, "dismissed");
    } catch {
      // Подсказка просто вернётся в следующей сессии.
    }
  }

  return (
    <div className="hub-hint">
      <p>{children}</p>
      <button aria-label="Скрыть подсказку" type="button" onClick={dismiss}><Icon name="xCircle" size={13} /></button>
    </div>
  );
}
