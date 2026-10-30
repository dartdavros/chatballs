// «{Сервис} подключён» показывается один раз — в карточке сразу после подключения.
// Карточка открывается переходом по адресу, поэтому отметка живёт в sessionStorage.
const KEY = "chatballs.services.connected";

export function markConnected(id: number): void {
  window.sessionStorage.setItem(KEY, String(id));
}

export function takeConnected(id: number): boolean {
  const marked = window.sessionStorage.getItem(KEY) === String(id);
  if (marked) window.sessionStorage.removeItem(KEY);
  return marked;
}
