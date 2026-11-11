import { PROVIDERS, type IntegrationKind, type IntegrationProvider } from "./model";

export function integrationProviderOptions(kind: IntegrationKind, allowedProviders?: readonly IntegrationProvider[]): Array<[string, string]> {
  return (Object.keys(PROVIDERS) as IntegrationProvider[])
    .filter(provider => (PROVIDERS[provider].kind === kind
      || kind === "LLM_PROVIDER" && PROVIDERS[provider].kind === "SPEECH_PROVIDER")
      && (!allowedProviders || allowedProviders.includes(provider)))
    .sort((left, right) => Number(left === "YANDEX_SPEECHKIT") - Number(right === "YANDEX_SPEECHKIT"))
    .map(provider => [provider, PROVIDERS[provider].label]);
}
