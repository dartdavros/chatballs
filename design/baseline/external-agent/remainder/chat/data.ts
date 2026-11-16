// Illustrative design-document content, never an API response or seeded conversation.
import { agentColorOf, groupColorOf } from '../../../../../apps/internal-ui/src/features/conversations/model';
import type { ConversationListItem } from '../../../../../apps/internal-ui/src/features/conversations/types';
import { fmt, t } from '../../../../../apps/internal-ui/src/i18n';
import { chatMode, type ChatId } from './cases';
import { tx } from './copy';
import { templateContent } from './template-data';

export const noop = () => {};
export const agentColor = agentColorOf(1);
export const timeLabel = (minute = 30) => fmt.time(new Date(Date.UTC(2026, 10, 15, 11, minute)));
export const dateLabel = fmt.dayMonthLong(new Date('2026-11-15T11:30:00Z'));
export const queueCountFor = (id: ChatId) => chatMode(id) === 'waiting' ? 1 : 0;
function lastPublicMessage(id: ChatId): { preview: string; minute: number; ours: boolean; voice?: boolean } {
  if (id === 'S52' || id === 'S53') return { preview: t('conversations.voice_message_duration', { duration: '0:12' }), minute: 30, ours: false, voice: true };
  if (id === 'S45' || id === 'S46') return { preview: tx('staffReply'), minute: 32, ours: true };
  if (id === 'S51') return { preview: tx('initiative'), minute: 40, ours: true };
  if (id === 'S43' || id === 'S54') return { preview: templateContent().text, minute: 31, ours: true };
  if (id === 'S42' || id === 'S50') return { preview: tx('reply'), minute: 31, ours: true };
  return { preview: tx('question'), minute: 30, ours: false };
}
export function dialogFor(id: ChatId): ConversationListItem {
  const mode = chatMode(id), last = lastPublicMessage(id);
  return {
    id: 1, name: tx('contactName'), initials: tx('contactInitials'), avatarBg: groupColorOf(2), channel: id === 'S54' ? 'TG' : 'WEB', email: '',
    mode: mode === 'human' ? 'operator' : mode === 'waiting' ? 'wait' : 'ai',
    preview: last.preview, time: timeLabel(last.minute), unread: 0,
    isMine: mode === 'human', priority: 'MEDIUM', labels: [], agentName: tx('agentName'), agentColor,
    groupName: tx('groupName'), groupColor: groupColorOf(1), waitLabel: mode === 'waiting' ? '2:00' : null,
    mineLabel: null, lastIsOurs: last.ours, lastIsVoice: Boolean(last.voice),
  };
}
export function otherDialog(id: ChatId): ConversationListItem {
  return { ...dialogFor(id), id: 2, name: tx('otherName'), initials: tx('otherInitials'), mode: 'closed',
    preview: tx('previewOther'), time: timeLabel(10), isMine: false, waitLabel: null, lastIsVoice: false, lastIsOurs: false, priority: 'NONE' };
}
