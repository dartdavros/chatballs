import { Button } from '../../../../../apps/internal-ui/src/shared/ui-controls';
import { LoadingState } from '../../../../../apps/internal-ui/src/shared/ui';
import { ServiceAlert } from '../../../../../apps/internal-ui/src/features/integrations/services/connect/ServiceAlert';
import { tx } from './copy';

export function SettingsLoadState({ failed }: { failed: boolean }) {
  return <section className="administration-card" style={{ minHeight: 440 }} data-settings-load={failed ? 'error' : 'pending'}>
    <div className="settings-card-head"><div><strong>{tx(failed ? 'title' : 'loading')}</strong></div></div>
    {failed ? <div className="external-load-error">
      <div role="alert" data-load-error-alert><ServiceAlert tone="error" title={tx('loadError')} text={tx('loadErrorHelp')} /></div>
      <div><Button variant="primary" onClick={() => {}}>{tx('retry')}</Button></div>
    </div> : <LoadingState />}
  </section>;
}
