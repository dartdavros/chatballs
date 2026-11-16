import { Icon } from '../../../../../apps/internal-ui/src/shared/icons';
import { ContactAvatar } from '../../../../../apps/internal-ui/src/features/conversations/ContactAvatar';
import { statusFor } from '../../../../../apps/internal-ui/src/features/conversations/data';
import { providerMeta } from '../../../../../apps/internal-ui/src/shared/providers';
import { t } from '../../../../../apps/internal-ui/src/i18n';
import { chatMode, type ChatId } from './cases';
import { dialogFor, timeLabel } from './data';
import { tx } from './copy';

// ClientContext and DialogControls presentation without data-loading/mutation children.
export function ChatContext({ variant }: { variant: ChatId }) {
  const dialog = dialogFor(variant), mode = chatMode(variant), status = statusFor(mode), channel = providerMeta[dialog.channel];
  return <aside className="sales-context">
    <div className="sales-context-tabs"><button className="active" type="button">{tx('contextTab')}</button><button type="button">{tx('historyTab')}</button>
      <button className="ctx-close" type="button" aria-label={t('common.close')}><Icon name="close" size={16} /></button></div>
    <div className="sales-context-body"><div className="sales-client-context">
      <div className="ctx-contact">
        <div className="ctx-contact-hero"><ContactAvatar initials={dialog.initials} background={dialog.avatarBg} className="ctx-contact-avatar" />
          <span className="ctx-channel-pill" style={{ color: channel.color, background: `color-mix(in srgb, ${channel.color} 14%, var(--surface-card))` }}><i style={{ background: channel.color }} />{channel.label}</span></div>
        <div className="ctx-contact-name"><strong>{dialog.name}</strong><button className="ctx-edit-contact" type="button" aria-label={t('sales.edit_contact')}><Icon name="edit" size={14} /></button></div>
        <p className="ctx-contact-description">{tx('contactDescription')}</p>
        <div className="ctx-contact-fields"><div className="ctx-contact-field is-muted"><span><Icon name="message" size={15} /></span><span>{dialog.channel === 'WEB' ? t('sales.anonymous_session', { channel: channel.label, connection: tx('groupName') }) : `${channel.label} · ${tx('groupName')}`}</span></div></div>
        <button className="ctx-request-contact" type="button">{t('sales.request_contact_details')}</button>
      </div>
      <section className="ctx-section"><div className="ctx-section-head"><h4>{t('conversations.conversation')}</h4><button type="button" aria-label={t('conversations.collapse')}><Icon name="chevron" size={14} /></button></div>
        <div className="ctx-fields">
          {mode === 'waiting' && <div className="ctx-waiting"><div className="ctx-waiting-head"><Icon name="clock" size={15} /><strong>{status.label}</strong></div><p>{tx('queueHelp')}</p></div>}
          <label className="ctx-label">{t('common.assignee')}</label>
          <button className="ctx-select" type="button"><Icon name="user" size={14} /><span>{mode === 'human' ? tx('operatorName') : t('conversations.unassigned')}</span><Icon name="chevron" size={14} /></button>
          <label className="ctx-label">{t('common.group')}</label><button className="ctx-select" type="button"><i className="ctx-dot" style={{ background: dialog.groupColor }} /><span>{dialog.groupName}</span><Icon name="chevron" size={14} /></button>
          <label className="ctx-label">{t('conversations.priority')}</label><button className="ctx-select" type="button"><span>{t('conversations.medium')}</span><Icon name="chevron" size={14} /></button>
          <div className="ctx-grid"><div><label className="ctx-label">{t('common.agent')}</label><div className="ctx-readonly" style={{ color: dialog.agentColor }}><Icon name="robot" size={14} />{dialog.agentName}</div></div>
            <div><label className="ctx-label">{t('conversations.mode')}</label><div className="ctx-readonly is-mode" style={{ color: status.color, background: status.bg, borderColor: status.border }}><i style={{ background: status.dot }} />{status.label}</div></div></div>
          <div className="ctx-meta-row"><span>{t('conversations.started')}</span><span>{timeLabel()}</span></div>
        </div>
      </section>
      <section className="ctx-section is-note"><div className="ctx-section-head"><h4>{t('conversations.note')}</h4></div><div className="ctx-note is-empty">{t('conversations.no_notes')}</div></section>
    </div></div>
  </aside>;
}
