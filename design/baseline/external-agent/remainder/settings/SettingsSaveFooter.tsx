import { LogoSpinner } from '../../../../../apps/internal-ui/src/shared/icons';
import { Button } from '../../../../../apps/internal-ui/src/shared/ui-controls';
import { ServiceAlert } from '../../../../../apps/internal-ui/src/features/integrations/services/connect/ServiceAlert';
import { tx } from './copy';

export function SettingsSaveFooter({ variant, edited }: { variant: string; edited: boolean }) {
  const saving = variant === 'S34', failed = variant === 'S35', enableFailed = variant === 'S72';
  const dirty = edited || ['S33', 'S35'].includes(variant);
  const state = enableFailed ? 'feature-enable-error' : saving ? 'saving' : failed ? 'error' : dirty ? 'unsaved' : 'saved';
  return <footer className="external-save-footer" data-save-state={state} aria-busy={saving}>
    {failed && <div role="alert" data-save-error-alert><ServiceAlert tone="error" title={tx('saveErrorTitle')} text={tx('saveErrorHelp')} /></div>}
    <div className="administration-actions" data-save-actions>
      {!saving && <small className="administration-saved">{tx(enableFailed ? 'enableStillOff' : dirty ? 'unsaved' : 'saved')}</small>}
      <Button variant="primary" disabled={(!dirty && !enableFailed) || saving} onClick={() => {}}>
        {saving && <span aria-hidden="true"><LogoSpinner size={14} /></span>}
        <span data-save-label>{tx(enableFailed ? 'retryEnable' : saving ? 'saving' : 'save')}</span>
      </Button>
    </div>
  </footer>;
}
