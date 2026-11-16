// Illustrative content for a static design document; never used as API responses.
import type { AgentCard } from '../../../apps/internal-ui/src/features/agents/model';
import type { SessionUser, EmployeeGroup } from '../../../apps/internal-ui/src/types';
import { tx } from './copy';

export const card: AgentCard = {
  id: 1, aiAgentId: 1, code: 'assistant', name: tx('agentName'), isActive: true,
  groupId: 1, groupName: tx('group'), groupColor: '#1677ff', aiStatus: 'DRAFT', assistanceEnabled: true,
  providerIntegrationId: 2, providerModel: '', model: '', modelSupportsTools: null,
  transcriptionIntegrationId: 3, transcriptionModel: '', transcriptionProviderModel: '', transcriptionLanguage: '',
  synthesisIntegrationId: null, synthesisModel: '', synthesisVoice: '', modelParams: {},
  answerLanguage: 'MIRROR', historyLimit: 20, persona: '', tone: '', instructions: '',
  knowledge: [], portalArticles: [], knowledgeTotal: 0,
  connections: [{ id: 4, provider: 'WEB', name: tx('organization'), status: 'OK',
    botUsername: '', email: '', allowedOrigins: ['https://obed.ru'], widgetPublicKey: '' }],
  counters: { openConversations: 0, connections: 1 }, createdAt: '2026-11-15T09:00:00Z', updatedAt: '2026-11-15T09:00:00Z',
};
export const groups: EmployeeGroup[] = [{ id: 1, name: tx('group'), color: '#1677ff', memberCount: 3, memberIds: [], createdAt: card.createdAt }];
export const user = {
  id: 1, fullName: tx('owner'), email: '', role: 'OWNER', organizationName: tx('organization'),
  organizationPublicId: 'design', organizationLogoUrl: null, organization: 'design', groups: [],
  capabilities: [], isInstanceAdmin: false, deliveryMode: 'SELF_HOSTED',
  memberships: [{ role: 'OWNER', organizationPublicId: 'design', organizationName: tx('organization') }],
} as SessionUser;
export const speechProviders = [{ id: 3, name: 'SpeechKit', isActive: true, status: 'OK', kind: 'SPEECH_PROVIDER',
  speechCapabilities: { stt: true, tts: true, default_model: 'general', voices: [] } }];
