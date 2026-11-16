import type { MouseEvent } from 'react';
import { Icon } from '../../../../../apps/internal-ui/src/shared/icons';
import { WorkbenchSidebar } from '../../settings-off/WorkbenchSidebar';
import { ExternalSettingsNavigation } from '../../settings-off/ExternalSettingsNavigation';
import '../../../../../apps/internal-ui/src/features/settings/styles.css';
import '../../../../../apps/internal-ui/src/features/integrations/services/services.css';
import '../../../../../apps/internal-ui/src/features/integrations/site-fields/styles.css';
import '../../../../../apps/internal-ui/src/features/employees/styles-create.css';
import { SettingsBody } from './SettingsBody';
import { tx } from './copy';
import './form-spacing.css';

export { settingsCases } from './cases';

function keepStatic(event: MouseEvent<HTMLDivElement>) {
  if ((event.target as Element).closest('a, .work-status-trigger, .settings-head-back')) {
    event.preventDefault(); event.stopPropagation();
  }
}

// Current settings shell; only the new external-execution contents vary.
export function SettingsSuite({ variant, width, height }: { variant: string; width: number; height: number }) {
  const mobile = width <= 900;
  return <div className="ea-screen" data-screen={variant} data-suite="settings" style={{ width, height }} onClickCapture={keepStatic}>
    <div className="hub-shell is-settings-route">
      <WorkbenchSidebar />
      <div className="hub-main"><main className="hub-scroll settings-scroll"><div className="hub-page settings-page">
        <div className="settings-layout"><ExternalSettingsNavigation hidden={mobile} />
          <section className={`settings-content ${mobile ? 'is-single' : ''}`}><div className="settings-content-inner">
            <header className="settings-head">{mobile && <button type="button" className="settings-head-back" aria-label={tx('back')}><Icon name="chevronLeft" size={18} /></button>}
              <div><h2>{tx('title')}</h2></div></header>
            <SettingsBody variant={variant} width={width} />
          </div></section>
        </div>
      </div></main></div>
    </div>
  </div>;
}
