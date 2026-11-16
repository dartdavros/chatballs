import { Icon } from '../../../../../apps/internal-ui/src/shared/icons';
import { SearchInput } from '../../../../../apps/internal-ui/src/shared/ui-controls';
import { DialogListItem } from '../../../../../apps/internal-ui/src/features/conversations/DialogListItem';
import { t } from '../../../../../apps/internal-ui/src/i18n';
import type { ChatId } from './cases';
import { dialogFor, otherDialog, noop, queueCountFor } from './data';

// Current DialogList markup; static width instead of the persistence/resize hook.
export function ChatList({ variant }: { variant: ChatId }) {
  const queueCount = queueCountFor(variant);
  return <section className="sales-dialog-list" style={{ '--dialog-list-width': '323px' } as React.CSSProperties}>
    <div className="sales-dialog-list-head"><div>
      <h2 className="sales-dialog-list-title">{t('common.conversations')}<small>2</small></h2>
      <span className="sales-dialog-list-tools">
        <button type="button" aria-label={t('conversations.sorting')}><Icon name="sort" size={15} /></button>
        <button type="button" aria-label={t('conversations.hide_list')}><Icon name="collapseLeft" size={15} /></button>
      </span>
    </div><SearchInput className="sales-dialog-search" placeholder={t('conversations.search_by_contact_or_message')} value="" onChange={noop} hotkey="/" /></div>
    <div className="sales-dialog-tabs">
      <button className="active" type="button">{t('common.all')}</button>
      <button type="button">{t('conversations.mine')}</button>
      <button type="button">{t('conversations.common_queue')}{queueCount > 0 && <b>{queueCount}</b>}</button>
      <button type="button">{t('conversations.on_me')}</button>
    </div>
    <div className="sales-dialog-list-body">
      <DialogListItem dialog={dialogFor(variant)} active setSelectedId={noop} />
      <DialogListItem dialog={otherDialog(variant)} active={false} setSelectedId={noop} />
    </div>
  </section>;
}
