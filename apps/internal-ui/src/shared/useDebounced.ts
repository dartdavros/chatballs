import { useEffect, useState } from "react";

// Ввод в поиске придерживается: запрос уходит, когда человек перестал печатать.
// Один хук на все списки — фильтры у них серверные, и каждая буква иначе шла бы
// в базу.
const DEFAULT_DELAY_MS = 300;

export function useDebounced<T>(value: T, delay = DEFAULT_DELAY_MS): T {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delay);
    return () => clearTimeout(timer);
  }, [delay, value]);
  return settled;
}
