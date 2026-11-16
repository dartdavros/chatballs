import { agent, speechProviders } from '../../agent-external/design-data';
import { tx } from './copy';
export { agent, groups, speechProviders, noop, unchanged } from '../../agent-external/design-data';
export const builtIn = { ...agent, persona: tx('persona'), tone: tx('tone'), instructions: tx('instructions'),
  providerModel: tx('model') };
export const providers = [{ ...speechProviders[0], id: 2, kind: 'LLM_PROVIDER' as const,
  provider: 'CUSTOM' as const, name: tx('llmName'), speechCapabilities: undefined,
  config: { ...speechProviders[0].config, defaultModel: tx('model') } }, ...speechProviders];
export const withoutLlm = { ...agent, providerIntegrationId: null, assistanceEnabled: false };
