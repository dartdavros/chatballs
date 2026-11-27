import { useState } from "react";
import { t } from "../../../i18n";
import { LauncherPreview } from "./LauncherPreview";
import { headerIconUrl, type WidgetAppearance } from "./model";
import { WidgetIcon } from "./WidgetIcon";
import "./preview.css";

/** Упрощённая копия из W3; демонстрационные реплики принадлежат макету. */
export function AppearancePreview({ appearance, launcherCss }: { appearance: WidgetAppearance; launcherCss: string }) {
  const side = { [appearance.launcherPosition]: 16 };
  const [customHeight, setCustomHeight] = useState(0);
  return <aside className="widget-appearance-preview" aria-label={t("widget_appearance.preview")}>
    <span className="widget-preview-label">{t("widget_appearance.preview")}</span>
    <div className="widget-preview-site">
      <span className="widget-preview-domain">{t("widget_appearance.preview_page", { domain: "obed.ru" })}</span>
      <div className="widget-preview-panel" data-widget-theme={appearance.theme} style={{ ...side, bottom: (launcherCss ? customHeight || appearance.launcherSize : appearance.launcherSize) + 28 }}>
        <div className="widget-preview-header">
          <WidgetIcon url={headerIconUrl(appearance)} size={28} />
          <span>{t("widget_appearance.preview_agent")}</span>
          <i><svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M5 12h14" /></svg></i>
        </div>
        <div className="widget-preview-body">
          <div className="widget-preview-bubble is-agent">{t("widget_appearance.preview_greeting")}</div>
          <div className="widget-preview-bubble is-client">{t("widget_appearance.preview_client")}</div>
        </div>
        <div className="widget-preview-composer"><span>{t("widget_appearance.preview_message")}</span><i><svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 19V5m-7 7 7-7 7 7" /></svg></i></div>
      </div>
      <LauncherPreview appearance={appearance} css={launcherCss} onHeight={setCustomHeight} />
    </div>
  </aside>;
}
