import { OrganizationSwitcher } from '../../../../apps/internal-ui/src/layout/OrganizationSwitcher';
import { SidebarNavigation } from '../../../../apps/internal-ui/src/layout/SidebarNavigation';
import { SidebarUserMenu } from '../../../../apps/internal-ui/src/layout/SidebarUserMenu';
import { NavigationIcon } from '../../../../apps/internal-ui/src/layout/NavigationIcon';
import { Icon, LogoIcon } from '../../../../apps/internal-ui/src/shared/icons';
import { PresenceDot, WorkStatusIcon } from '../../../../apps/internal-ui/src/features/work-status/WorkStatusLabel';
import { t } from '../../../../apps/internal-ui/src/i18n';
import { user, workStatus } from './design-data';

const noop = () => {};
// Current Sidebar presentation, without mounting its presence/realtime hooks.
export function WorkbenchSidebar() {
  const initials = user.fullName.split(/\s+/).map(part => part[0] ?? '').join('').slice(0, 2).toUpperCase();
  return <aside className="hub-sidebar">
    <div className="hub-rail">
      <div className="hub-brand-mark"><LogoIcon /></div>
      <button className="hub-rail-button" type="button" title={t('common.chat')}><Icon name="message" size={18} strokeWidth={1.9} /></button>
      <button className="hub-rail-button" type="button" title={t('profile.expand')}><NavigationIcon name="expand" /></button>
      <div className="hub-rail-spacer" />
      <button className="hub-rail-avatar" type="button" title={user.fullName}>{initials}<PresenceDot online own /><WorkStatusIcon code="READY" size={14} /></button>
    </div>
    <div className="hub-sidebar-body">
      <OrganizationSwitcher user={user} setRoute={noop} onSwitchOrganization={noop} />
      <SidebarNavigation user={user} route="settings" setRoute={noop} waitingCount={0}
        chatScope="all" setChatScope={noop} chatCounters={null} />
      <SidebarUserMenu user={user} route="settings" setRoute={noop} onLogout={noop} workStatus={workStatus} />
    </div>
  </aside>;
}
