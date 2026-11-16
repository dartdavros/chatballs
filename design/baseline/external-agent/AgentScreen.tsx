import type { MouseEvent } from 'react';
import { t } from '../../../apps/internal-ui/src/i18n';
import { OrganizationSwitcher } from '../../../apps/internal-ui/src/layout/OrganizationSwitcher';
import { SidebarNavigation } from '../../../apps/internal-ui/src/layout/SidebarNavigation';
import { NavigationIcon } from '../../../apps/internal-ui/src/layout/NavigationIcon';
import { Avatar } from '../../../apps/internal-ui/src/shared/ui';
import { Icon, LogoIcon } from '../../../apps/internal-ui/src/shared/icons';
import { BackLink } from '../../../apps/internal-ui/src/shared/ui-controls';
import { AssignmentCard } from '../../../apps/internal-ui/src/features/agents/AssignmentCard';
import { AssistanceCard } from '../../../apps/internal-ui/src/features/agents/AssistanceCard';
import { ConnectionsCard } from '../../../apps/internal-ui/src/features/agents/ConnectionsCard';
import { card, groups, user } from './design-data';
import { ExecutionCard } from './ExecutionCard';
import { PermissionsCard } from './PermissionsCard';
import { AgentHeader } from './AgentHeader';
import { SpeechCard } from './SpeechCard';

const noop = () => {};
const unchanged = async () => false;

function keepContextStatic(event: MouseEvent<HTMLDivElement>) {
  const target = event.target as Element;
  // Context switches would otherwise run the product's saving state machine.
  // Leave shared selection menus available for inspecting their real appearance.
  if (target.closest('a, .agent-assistance-toggle button, .agent-connection-action, .agent-card-head .link, .hub-rail-button, .profile-more')) {
    event.preventDefault(); event.stopPropagation();
  }
}

// Shell presentation follows Sidebar.tsx; presence/session hooks are not mounted.
function Sidebar() {
  return <aside className="hub-sidebar">
    <div className="hub-rail">
      <div className="hub-brand-mark"><LogoIcon /></div>
      <button className="hub-rail-button" type="button" title={t('common.chat')}><Icon name="message" size={18} /></button>
      <button className="hub-rail-button" type="button" title={t('profile.expand')}><NavigationIcon name="expand" /></button>
      <div className="hub-rail-spacer" /><button className="hub-rail-avatar" type="button" title={user.fullName}>{user.fullName.slice(0, 1)}</button>
    </div>
    <div className="hub-sidebar-body">
      <OrganizationSwitcher user={user} setRoute={noop} onSwitchOrganization={noop} />
      <SidebarNavigation user={user} route="agentDetail" setRoute={noop} waitingCount={0}
        chatScope="all" setChatScope={noop} chatCounters={null} />
      <div className="profile-link"><span className="profile-avatar"><Avatar user={user} /></span>
        <span><strong>{user.fullName}</strong></span>
        <button type="button" className="row-menu-button profile-more" aria-label={t('profile.user_menu')}><Icon name="more" size={16} /></button>
      </div>
    </div>
  </aside>;
}

export function AgentScreen({ width, height }: { width: number; height: number }) {
  return <div className="ea-screen" data-screen="A01" style={{ width, height }} onClickCapture={keepContextStatic}>
    <div className="hub-shell">
      <Sidebar />
      <main className="hub-main">
        <div className="hub-scroll agents-scroll">
          <div className="hub-page agents-page-shell">
            <div className="agent-page">
              <BackLink label={t('common.agents')} onClick={noop} />
              <AgentHeader />
              <div className="agent-grid">
                <div className="agent-column">
                  <ExecutionCard />
                  <PermissionsCard />
                  <SpeechCard />
                </div>
                <div className="agent-column">
                  <AssignmentCard card={card} groups={groups} canManage busy={false} apply={unchanged} />
                  <AssistanceCard card={card} canManage busy={false} save={unchanged} />
                  <ConnectionsCard card={card} canManage busy={false} available={[]} openChannels={noop} bind={noop} unbind={noop} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>;
}
