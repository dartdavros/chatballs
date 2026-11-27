import type { CSSProperties } from "react";

import { t } from "../../../i18n";
import { Button } from "../../../shared/ui-controls";
import { Segmented } from "../../../shared/ui";
import type { Integration } from "../model";
import { AppearancePreview } from "./AppearancePreview";
import { ColorSettings } from "./ColorSettings";
import { CssSettings } from "./CssSettings";
import { IconSettings } from "./IconSettings";
import { LauncherSettings } from "./LauncherSettings";
import { useAppearance } from "./useAppearance";
import "./settings.css";

export function WebIntegrationAppearance({ integration, onSaved }: {
  integration: Integration; onSaved: (integration: Integration) => void;
}) {
  const state = useAppearance(integration, onSaved);
  return <div className="widget-appearance-layout" style={{ "--widget-accent": state.appearance.accent } as CSSProperties}>
    <div className="widget-appearance-controls">
      <div className="portal-settings-heading">
        <h3>{t("common.appearance")}</h3><p>{t("widget_appearance.description")}</p>
      </div>
      <div className="widget-appearance-card">
        <span className="widget-appearance-label">{t("widget_appearance.theme")}</span>
        <Segmented className="is-content-width" items={[["light", t("widget_appearance.theme_light")], ["dark", t("widget_appearance.theme_dark")]]}
          value={state.appearance.theme} setValue={(theme: "light" | "dark") => state.change({ theme })} />
      </div>
      <ColorSettings accent={state.appearance.accent} customHex={state.customHex} custom={state.custom}
        onPreset={state.pickPreset} onHex={state.changeHex} />
      <IconSettings integrationId={integration.id} appearance={state.appearance} onChange={state.change} onBusy={state.uploadBusy} />
      <LauncherSettings appearance={state.appearance} onChange={state.change} />
      <CssSettings value={state.appearance.customCss} onChange={(customCss) => state.change({ customCss })} />
      <div className="portal-settings-actions">
        <Button variant="primary" disabled={state.busy} onClick={() => void state.save()}>{t("widget_appearance.save")}</Button>
        <Button variant="secondary" onClick={() => state.change({ customCss: "" })}>{t("widget_appearance.reset")}</Button>
        <span className="portal-settings-gap" />
        {state.dirty && <span className="portal-settings-note">{t("widget_appearance.unsaved")}</span>}
      </div>
      {state.error && <div className="integration-form-error" role="alert">{state.error}</div>}
    </div>
    <AppearancePreview appearance={state.appearance} launcherCss={state.launcherPreviewCss} />
  </div>;
}
