export type Surface = "app" | "help" | "loading";

export function surfaceForHost(hostname: string, configuredAppHost = ""): Surface {
  const normalized = hostname.toLocaleLowerCase();
  const appHost = configuredAppHost.toLocaleLowerCase();
  if (
    normalized === "localhost"
    || normalized === "127.0.0.1"
    || normalized === "app.localhost"
    || (appHost !== "" && normalized === appHost)
  ) {
    return "app";
  }
  // Поддомены localhost — порталы помощи dev-стека; прочие хосты определяет
  // бэкенд (пробa /api/v1/help/ в main.tsx), зашитых доменов нет.
  if (normalized.endsWith(".localhost")) {
    return "help";
  }
  return "loading";
}
