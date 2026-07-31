import { useEffect, useState } from "react";

// Секундомер активного соединения: стартует при `active=true`, фиксирует момент
// старта и тикает раз в секунду. Используется и аудио-, и видеостадией звонка.
export function useConnectionTimer(active: boolean): number {
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    if (!active) return;
    const origin = startedAt ?? Date.now();
    if (startedAt == null) setStartedAt(origin);
    const update = () => setSeconds(Math.floor((Date.now() - origin) / 1000));
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, [active, startedAt]);
  return seconds;
}
