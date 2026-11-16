import { Icon } from '../../../../../apps/internal-ui/src/shared/icons';
import { ContactAvatar } from '../../../../../apps/internal-ui/src/features/conversations/ContactAvatar';
import { statusFor } from '../../../../../apps/internal-ui/src/features/conversations/data';
import { providerMeta } from '../../../../../apps/internal-ui/src/shared/providers';
import { t } from '../../../../../apps/internal-ui/src/i18n';
import { chatMode, type ChatId } from './cases';
import { dialogFor } from './data';

export function ChatHead({ variant }: { variant: ChatId }) {
  const dialog = dialogFor(variant), mode = chatMode(variant), status = statusFor(mode), channel = providerMeta[dialog.channel];
  return <div className="sales-conversation-head">
    <button className="mobile-back" type="button" aria-label={t('conversations.back_conversation_list')}><Icon name="arrow" size={19} /></button>
    <div className="sales-conversation-person">
      <span className="sales-conversation-avatar-wrap"><ContactAvatar initials={dialog.initials} background={dialog.avatarBg} className="sales-conversation-avatar" /><i style={{ background: status.dot }} /></span>
      <div><strong>{dialog.name}</strong><p>
        <span className="is-status" style={{ color: status.color }}>{status.label}</span><i />
        <span><em style={{ background: channel.color }} />{channel.label}</span><i />
        <span className="is-agent" style={{ color: dialog.agentColor }}><Icon name="robot" size={13} />{dialog.agentName}</span><i /><span>{dialog.groupName}</span>
      </p></div>
    </div>
    <div className="sales-conversation-actions">
      {mode === 'human'
        ? <button className="sales-secondary-action" type="button">{t('conversations.hand_back_ai')}</button>
        : <button className="sales-claim-button" type="button"><Icon name="check" size={15} />{t('conversations.take_conversation')}</button>}
      <button className="ctx-toggle ui-icon-button" type="button" aria-label={t('conversations.conversation_context')}><Icon name="user" size={16} /></button>
      <button className="sales-more-button" type="button" aria-label={t('common.actions')}><Icon name="more" size={17} /></button>
    </div>
  </div>;
}
