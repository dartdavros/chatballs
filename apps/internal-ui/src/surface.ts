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
  if (
    normalized.endsWith(".localhost")
    || normalized.endsWith(".help.custocrm.ru")
  ) {
    return "help";
  }
  return "loading";
}
