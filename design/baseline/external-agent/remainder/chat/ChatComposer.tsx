import { Icon } from '../../../../../apps/internal-ui/src/shared/icons';
import { ComposerAudienceBar } from '../../../../../apps/internal-ui/src/features/conversations/ComposerAudienceBar';
import { ComposerWarning } from '../../../../../apps/internal-ui/src/features/conversations/ComposerWarning';
import { ComposerDraftButton } from '../../../../../apps/internal-ui/src/features/conversations/ComposerDraftButton';
import { TokenEditor } from '../../../../../apps/internal-ui/src/features/reply-templates/TokenEditor';
import { EmojiPicker } from '../../../../../apps/internal-ui/src/features/conversations/EmojiPicker';
import { providerMeta } from '../../../../../apps/internal-ui/src/shared/providers';
import { t } from '../../../../../apps/internal-ui/src/i18n';
import { chatMode, type ChatId } from './cases';
import { tx } from './copy';
import { dialogFor, noop } from './data';

// Current composer presentation: no model/data hooks, file input, recorder or send operation.
export function ChatComposer({ variant, compact }: { variant: ChatId; compact: boolean }) {
  return <div className="sales-composer"><div className="composer-wrap">
    <ComposerWarning mode={chatMode(variant)} />
    <div className="composer-box">
      <ComposerAudienceBar audience="reply" channelLabel={providerMeta[dialogFor(variant).channel].label} compact={compact} onChange={noop} />
      <div className="composer-field"><TokenEditor label={t('conversations.message')} placeholder={t(compact ? 'conversations.message' : 'conversations.type_message_shift_enter_line')}
        value="" variables={[]} onChange={noop} onKeyDown={event => event.preventDefault()} onPaste={event => event.preventDefault()} /></div>
      <div className="composer-toolbar">
        <EmojiPicker onPick={noop} />
        <button className="composer-tool" type="button" aria-label={t('common.attach_file')}><Icon name="paperclip" size={17} /></button>
        <button className="composer-tool" type="button" aria-label={t('conversations.record_voice_message')}><Icon name="mic" size={17} /></button>
        <button className="composer-tool is-labeled" type="button"><Icon name="text" size={16} />{t('conversations.templates')}</button>
        <ComposerDraftButton state="idle" agentName={tx('agentName')} onRequest={noop} />
        <span className="composer-spacer" />
        <button className="composer-send" type="button" disabled><span>{t('conversations.send')}</span><kbd>⏎</kbd><Icon name="send" size={17} /></button>
      </div>
    </div>
  </div></div>;
}
