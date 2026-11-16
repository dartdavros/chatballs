// Design-document examples only; no API response, session, credential or persisted consent.
import type { WebConfig } from '../../../../../apps/web-chat/src/api';
import type { ComposerAttachment, ComposerVoice } from '../../../../../apps/web-chat/src/ChatComposer';
import { clientText } from './copy';

export const noop = () => {};
export const widgetAccent = '#1677ff';
export const illustratedRevision = 'v2';

export function consentConfig(form: boolean): WebConfig {
  return {
    available: true, autonomous: true, title: clientText('title'), accent: widgetAccent,
    greeting: clientText('greeting'),
    consent: { text: clientText('proposedConsent'), version: illustratedRevision },
    features: { voiceMessages: true, audioCalls: false, videoCalls: false },
    fields: [],
    preChat: { enabled: form, title: clientText('formTitle'), fields: [
      { key: 'name', required: true }, { key: 'email', required: false },
    ] },
  };
}

export const idleVoice: ComposerVoice = {
  supported: true, state: 'idle', seconds: 0, errorText: '',
  start: async () => {}, stopAndSend: noop, cancel: noop,
};
export const emptyAttachment: ComposerAttachment = {
  file: null, errorText: '', pick: noop, clear: noop,
};
