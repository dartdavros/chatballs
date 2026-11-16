import { LogoSpinner } from "../../../shared/icons";
import { Button } from "../../../shared/ui-controls";
import { ServiceAlert } from "../../integrations/services/connect/ServiceAlert";
import { et } from "./copy";

export function SettingsSaveFooter({ busy, failed, dirty, disabled, save, enableFailed = false, retryEnable }: {
  busy: boolean; failed: boolean; dirty: boolean; disabled: boolean; save: () => void;
  enableFailed?: boolean; retryEnable?: () => void;
}) {
  return <footer className="external-save-footer" data-save-state={enableFailed ? "feature-enable-error" : busy ? "saving" : failed ? "error" : dirty ? "unsaved" : "saved"} aria-busy={busy}>
    {failed && <div role="alert"><ServiceAlert tone="error" title={et("feedback.saveErrorTitle")} text={et("feedback.saveErrorHelp")} /></div>}
    <div className="administration-actions">{!busy && <small className="administration-saved">{et(enableFailed ? "settings.enableStillOff" : dirty ? "settings.unsaved" : "settings.saved")}</small>}
      <Button variant="primary" disabled={busy || (!enableFailed && (disabled || !dirty))} onClick={enableFailed ? retryEnable : save}>
        {busy && <span aria-hidden="true"><LogoSpinner size={14} /></span>}<span>{et(enableFailed ? "settings.retryEnable" : busy ? "settings.saving" : "settings.save")}</span>
      </Button></div>
  </footer>;
}
