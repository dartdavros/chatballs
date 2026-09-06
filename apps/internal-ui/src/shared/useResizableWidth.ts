import { useCallback, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";

// Ширина панели, которую пользователь тянет за край: значение живёт в
// localStorage этого браузера и ограничено разумным диапазоном.

const STORAGE_PREFIX = "chatballs.ui.width.";

function readStored(key: string, fallback: number, min: number, max: number): number {
  try {
    const raw = window.localStorage.getItem(STORAGE_PREFIX + key);
    const value = raw ? Number(raw) : NaN;
    return Number.isFinite(value) ? Math.min(max, Math.max(min, value)) : fallback;
  } catch {
    return fallback;
  }
}

export function useResizableWidth(key: string, { fallback, min, max }: { fallback: number; min: number; max: number }) {
  const [width, setWidth] = useState(() => readStored(key, fallback, min, max));
  const [dragging, setDragging] = useState(false);
  const drag = useRef<{ startX: number; startWidth: number } | null>(null);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_PREFIX + key, String(width));
    } catch {
      /* без сохранения — ширина держится до перезагрузки */
    }
  }, [key, width]);

  const onPointerDown = useCallback((event: ReactPointerEvent<HTMLElement>) => {
    if (event.button !== 0) return;
    event.preventDefault();
    drag.current = { startX: event.clientX, startWidth: width };
    setDragging(true);
    const move = (moveEvent: PointerEvent) => {
      if (!drag.current) return;
      const next = drag.current.startWidth + moveEvent.clientX - drag.current.startX;
      setWidth(Math.min(max, Math.max(min, Math.round(next))));
    };
    const up = () => {
      drag.current = null;
      setDragging(false);
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }, [width, min, max]);

  const reset = useCallback(() => setWidth(fallback), [fallback]);

  return { width, dragging, onPointerDown, reset };
}
