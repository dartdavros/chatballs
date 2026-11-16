// Illustrative design document content. No fixture, API response or runtime binding.
import type { AgentCard } from '../../../../apps/internal-ui/src/features/agents/model';
import type { Integration } from '../../../../apps/internal-ui/src/features/integrations/model';
import type { EmployeeGroup } from '../../../../apps/internal-ui/src/types';
import { tx } from './copy';

export const noop = () => {};
export const unchanged = async () => false;
export const agent: AgentCard = {
  id: 1, aiAgentId: 1, code: 'assistant', name: tx('agentName'), isActive: true,
  groupId: 1, groupName: tx('groupName'), groupColor: '', aiStatus: 'DRAFT', assistanceEnabled: true,
  model: '', providerModel: '', providerIntegrationId: 2, modelParams: {}, modelSupportsTools: null,
  transcriptionIntegrationId: 3, transcriptionModel: '', transcriptionProviderModel: 'general', transcriptionLanguage: '',
  synthesisIntegrationId: null, synthesisModel: '', synthesisVoice: '',
  answerLanguage: 'MIRROR', historyLimit: 20, persona: '', tone: '', instructions: '',
  knowledge: [], portalArticles: [], knowledgeTotal: 0, tools: [],
  connections: [{ id: 4, provider: 'WEB', name: tx('channelName'), status: 'OK',
    botUsername: '', email: '', allowedOrigins: ['https://example.org'], widgetPublicKey: '' }],
  counters: { openConversations: 0, connections: 1 },
  createdAt: '2026-10-01T09:00:00Z', updatedAt: '2026-10-01T09:00:00Z',
};
export const groups: EmployeeGroup[] = [{ id: 1, name: tx('groupName'), color: '',
  memberCount: 0, memberIds: [], createdAt: '2026-10-01T09:00:00Z' }];
export const speechProviders: Integration[] = [{
  id: 3, kind: 'SPEECH_PROVIDER', provider: 'YANDEX_SPEECHKIT', name: tx('speechName'),
  speechCapabilities: { stt: true, tts: true, default_model: 'general', voices: [],
    models: [], languages: [], formats: [], max_bytes: 0, max_seconds: 0 },
  isActive: true, status: 'OK', hasSecret: true, secretMasked: '', lastCheckedAt: null, lastError: '',
  config: { baseUrl: '', defaultModel: '', transcriptionModel: '', proxyUrl: '',
    botId: '', botUsername: '', botName: '', purpose: '', allowedOrigins: [], title: '', accent: '',
    greeting: '', quickReplies: [], consentText: '', consentVersion: '', email: '',
    imapHost: '', imapPort: 993, imapSsl: true, smtpHost: '', smtpPort: 465, smtpSsl: true },
  channel: null, createdAt: '2026-10-01T09:00:00Z', updatedAt: '2026-10-01T09:00:00Z',
}];
