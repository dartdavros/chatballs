import { copy } from './copy';

export const chatIds = ['S40', 'S41', 'S42', 'S43', 'S44', 'S45', 'S46', 'S47', 'S48', 'S49', 'S50', 'S51', 'S52', 'S53', 'S54'] as const;
export type ChatId = typeof chatIds[number];
export const chatCases = chatIds.map(id => ({
  id, titleRu: copy.ru[`${id}title`], titleEn: copy.en[`${id}title`],
  descriptionRu: copy.ru[`${id}desc`], descriptionEn: copy.en[`${id}desc`],
}));
export function chatMode(id: ChatId): 'ai' | 'human' | 'waiting' {
  if (id === 'S45') return 'human';
  return ['S44', 'S47', 'S48', 'S49', 'S50', 'S53'].includes(id) ? 'waiting' : 'ai';
}
