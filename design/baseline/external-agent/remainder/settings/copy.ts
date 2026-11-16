import { core } from './copy.core';
import { policy } from './copy.policy';
import { caseCopy } from './copy.cases';
import { stateFeedback } from './copy.feedback';

export const copy = {
  ru: { ...core.ru, ...policy.ru, ...caseCopy.ru, ...stateFeedback.ru },
  en: { ...core.en, ...policy.en, ...caseCopy.en, ...stateFeedback.en },
};
export const language = new URLSearchParams(location.search).get('lang') === 'en' ? 'en' : 'ru';
export type CopyKey = keyof typeof copy.ru;
export const tx = (key: CopyKey) => copy[language][key];
