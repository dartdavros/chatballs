import { voiceWaveHeights } from '@chatballs/ui';
import { Icon } from '../../../../../apps/internal-ui/src/shared/icons';
import { t } from '../../../../../apps/internal-ui/src/i18n';
import { tx } from './copy';

// Current VoiceMessage presentation; playback/transcription cannot call services in the document.
export function VoiceBody({ transcribed }: { transcribed: boolean }) {
  return <div className="voice-message" data-voice-preserved>
    <div className="voice-message-player">
      <button className="voice-message-play" type="button" aria-label={t('conversations.play')}><Icon name="play" size={14} /></button>
      <span className="voice-message-wave">{voiceWaveHeights(1).map((height, index) => <i key={index} style={{ height }} />)}</span>
      {!transcribed && <button className="voice-message-transcribe" type="button" disabled><Icon name="text" size={13} />{t('conversations.transcribe')}</button>}
      <em>0:12</em>
    </div>
    {transcribed && <span className="voice-message-caption voice-message-show">{tx('voiceReady')}</span>}
  </div>;
}
