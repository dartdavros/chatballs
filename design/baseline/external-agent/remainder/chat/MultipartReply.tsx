import { PreparedMessage } from '@chatballs/ui';
import { ConversationText } from '../../../../../apps/internal-ui/src/features/conversations/ConversationText';
import { MessageBubble } from '../../../../../apps/internal-ui/src/features/conversations/MessageBubble';
import { Icon } from '../../../../../apps/internal-ui/src/shared/icons';
import { t } from '../../../../../apps/internal-ui/src/i18n';
import { formatSize } from '../../../../../apps/internal-ui/src/features/ai/knowledge/model';
import hero from '../../../../../apps/internal-ui/public/hero.png';
import { AiMessage } from './ChatMessages';
import { agentColor, timeLabel } from './data';
import { tx } from './copy';
import { templateContent } from './template-data';

// FileMessage markup with a bundled application image and inert file actions; no HTTP attachment URLs.
export function MultipartReply() {
  return <div data-multipart>
    <AiMessage text={tx('reply')} />
    <AiMessage><div className="file-message is-image">
      <button className="file-message-image" type="button" title={tx('imageName')}><img src={hero} alt={tx('imageName')} /></button>
      <div className="file-message-caption"><ConversationText text={tx('imageCaption')} /></div>
    </div></AiMessage>
    <AiMessage><div className="file-message"><div className="file-message-card">
      <span className="file-message-icon"><Icon name="paperclip" size={16} /></span>
      <div className="file-message-meta"><strong title={tx('fileName')}>{tx('fileName')}</strong><small>{formatSize(131072)}</small></div>
      <button className="link" type="button">{t('common.download')}</button>
    </div></div></AiMessage>
    <AiMessage text={tx('contactMessage')} />
    <AiMessage text={tx('contactRequest')} />
    <MessageBubble side="ai" actor={`AI · ${tx('agentName')}`} actorColor={agentColor} time={timeLabel(31)} formatted
      footer={<span className="conversation-snapshot-meta"><span><Icon name="layout" size={11} />{tx('orderTemplate')}</span></span>}>
      <PreparedMessage content={templateContent()} title={t('snapshots.message')} />
    </MessageBubble>
  </div>;
}
