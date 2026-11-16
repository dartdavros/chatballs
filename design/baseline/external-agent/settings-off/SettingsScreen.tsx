import type { MouseEvent } from 'react';
import { t } from '../../../../apps/internal-ui/src/i18n';
import { Icon } from '../../../../apps/internal-ui/src/shared/icons';
import { WorkbenchSidebar } from './WorkbenchSidebar';
import { ExternalSettingsNavigation } from './ExternalSettingsNavigation';
import { ExternalExecutionCard } from './ExternalExecutionCard';
import { tx } from './copy';

function keepContextStatic(event: MouseEvent<HTMLDivElement>) {
  const element = event.target as Element;
  if (element.closest('a, .work-status-trigger, .settings-head-back')) {
    event.preventDefault(); event.stopPropagation();
  }
}

export function SettingsScreen({ width, height }: { width: number; height: number }) {
  const mobile = width <= 900;
  return <div className="ea-screen" data-screen="S01" style={{ width, height }} onClickCapture={keepContextStatic}>
    <div className="hub-shell is-settings-route">
      <WorkbenchSidebar />
      <div className="hub-main">
        <main className="hub-scroll settings-scroll">
          <div className="hub-page settings-page">
            <div className="settings-layout">
              <ExternalSettingsNavigation hidden={mobile} />
              <section className={`settings-content ${mobile ? 'is-single' : ''}`}>
                <div className="settings-content-inner">
                  <header className="settings-head">
                    {mobile && <button type="button" className="settings-head-back" aria-label={t('settings.back_section_list')}><Icon name="chevronLeft" size={18} /></button>}
                    <div><h2>{tx('sectionTitle')}</h2></div>
                  </header>
                  <ExternalExecutionCard />
                </div>
              </section>
            </div>
          </div>
        </main>
      </div>
    </div>
  </div>;
}
