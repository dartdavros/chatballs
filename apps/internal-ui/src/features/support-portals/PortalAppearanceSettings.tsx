import { useEffect, useMemo, useState } from "react";

import { Icon } from "../../shared/icons";
import { Segmented } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import { shortDateTime } from "../../shared/utils";
import {
  listPortalThemes,
  resolvePortalTheme,
  schemeOptions,
} from "../help-center/themes/registry";
import type { PortalThemeManifest, PortalThemeSchemeSetting } from "../help-center/themes/types";
import { portalErrorMessage, updateSupportPortal, type SupportPortal } from "./model";
import { t } from "../../i18n";

// Кадр PT6: тема выбирается карточкой с мини-превью на цветах манифеста. Ни
// названия, ни описания, ни цвета в UI не придумываются — всё из манифеста
// темы (features/help-center/themes/*/manifest.ts).

function ThemePreview({ theme }: { theme: PortalThemeManifest }) {
  const { bg, ink, accent, radius = "5px" } = theme.preview;
  return (
    <span className="portal-theme-preview" style={{ background: bg }}>
      <span className="portal-theme-bar" style={{ background: ink }} />
      <span className="portal-theme-line" style={{ background: ink, width: "80%" }} />
      <span className="portal-theme-line" style={{ background: ink, width: "62%", marginBottom: 9 }} />
      <span className="portal-theme-tiles">
        <i style={{ background: accent, borderRadius: radius }} />
        <i style={{ background: accent, borderRadius: radius }} />
      </span>
    </span>
  );
}

export function PortalAppearanceSettings({
  canManage,
  portal,
  onChanged,
}: {
  canManage: boolean;
  portal: SupportPortal;
  onChanged: (portal: SupportPortal) => void;
}) {
  const [theme, setTheme] = useState(portal.theme);
  const [scheme, setScheme] = useState<PortalThemeSchemeSetting>(portal.themeScheme);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [savedAt, setSavedAt] = useState<string | null>(null);

  useEffect(() => {
    setTheme(portal.theme);
    setScheme(portal.themeScheme);
  }, [portal.theme, portal.themeScheme]);

  const themes = useMemo(listPortalThemes, []);
  const known = themes.some((item) => item.id === theme);
  const selected = resolvePortalTheme(theme);
  const schemes = schemeOptions(selected);
  // Схема, которую выбранная тема не поддерживает, не должна молча уехать в
  // сохранение: показываем ближайшую поддерживаемую.
  const effectiveScheme = schemes.some(([value]) => value === scheme) ? scheme : schemes[0][0];

  async function save() {
    setBusy(true);
    setFeedback("");
    try {
      const payload = await updateSupportPortal(portal.id, { theme, themeScheme: effectiveScheme });
      onChanged(payload.portal);
      setSavedAt(payload.portal.updatedAt);
    } catch (caught) {
      setFeedback(portalErrorMessage(caught, t("portals.could_not_save_appearance")));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="portal-settings-card">
      <div>
        <span className="portal-field-label">{t("profile.theme")}</span>
        <div className="portal-theme-grid">
          {themes.map((item) => (
            <button
              className={`portal-theme-card${item.id === theme ? " is-selected" : ""}`}
              disabled={!canManage}
              key={item.id}
              type="button"
              onClick={() => setTheme(item.id)}
            >
              <ThemePreview theme={item} />
              <span className="portal-theme-name">
                <strong>{item.name}</strong>
                {item.id === theme && <small>{t("portals.selected")}</small>}
              </span>
              <small className="portal-theme-desc">{item.description}</small>
            </button>
          ))}
          {!known && (
            // Темы больше нет в сборке: показываем как есть, чтобы сохранение
            // не подменило её молча.
            <span className="portal-theme-card is-missing">
              <span className="portal-theme-name"><strong>{theme}</strong><small>{t("portals.unavailable")}</small></span>
              <small className="portal-theme-desc">{t("portals.theme_not_installation_build_pick")}</small>
            </span>
          )}
        </div>
      </div>

      <div>
        <span className="portal-field-label">{t("portals.colour_scheme")}</span>
        <Segmented
          className="portal-scheme-segment"
          items={schemes}
          value={effectiveScheme}
          setValue={(value) => setScheme(value)}
        />
      </div>

      <div className="portal-settings-actions">
        {canManage && <Button variant="primary" disabled={busy} onClick={() => void save()}>{t("portals.save_appearance")}</Button>}
        <a className="secondary-button" href={portal.publicUrl} rel="noreferrer" target="_blank">
          <Icon name="eye" size={15} strokeWidth={1.9} />{t("portals.portal_preview")}</a>
        <span className="portal-settings-gap" />
        {savedAt && <span className="portal-settings-note">{t("portals.saved_at_lower", { date: shortDateTime(savedAt) })}</span>}
      </div>
      {feedback && <div className="portal-form-error">{feedback}</div>}
    </div>
  );
}
