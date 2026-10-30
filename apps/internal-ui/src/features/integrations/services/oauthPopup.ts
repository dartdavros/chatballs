// Окно входа в сервис возвращается на адрес вкладки «Сервисы» с отметкой
// serviceOauth=done (backend: service_connections/oauth_views.py). Результат
// форма подключения узнаёт по своему state, а само окно просто закрывается.
export function closeServiceOAuthWindow(): boolean {
  const done = new URLSearchParams(window.location.search).get("serviceOauth") === "done";
  if (!done || !window.opener) return false;
  window.close();
  return true;
}
