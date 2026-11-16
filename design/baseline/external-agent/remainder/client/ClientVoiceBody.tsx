import { Bubble, SystemMessage } from '../../../../../apps/web-chat/src/ChatMessages';
import { VoiceMessage } from '../../../../../apps/web-chat/src/VoiceMessage';
import { t } from '../../../../../apps/web-chat/src/i18n';
import { widgetClasses as classes } from '../../../../../apps/web-chat/src/widgetClasses';
import { clientText } from './copy';
import { widgetAccent } from './model';

// Existing Bubble composition with the actual VoiceMessage presentation; no audio asset.
export function ClientVoiceBody() {
  return <div className={classes.body}>
    <Bubble author="ai" authorName={clientText('title')} text={clientText('greeting')} accent={widgetAccent} />
    <div className={`${classes.message} ${classes.messageClient}`}>
      <div className={classes.messageContent}>
        <div className={`${classes.bubble} ${classes.bubbleClient} ${classes.bubbleAudio}`}
          style={{ '--cb-accent': widgetAccent } as React.CSSProperties}>
          <VoiceMessage messageId={1} url="" durationSeconds={12} accent={widgetAccent} light />
        </div>
        <div className={classes.messageTime}>12:00</div>
      </div>
    </div>
    <SystemMessage neutral text={t('chat.waiting_operator')} />
  </div>;
}
