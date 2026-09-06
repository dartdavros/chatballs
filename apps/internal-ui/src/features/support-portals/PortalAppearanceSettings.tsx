import { useEffect, useMemo, useState } from "react";

import { SelectField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import {
  listPortalThemes,
  resolvePortalTheme,
  schemeOptions,
} from "../help-center/themes/registry";
import type { PortalThemeSchemeSetting } from "../help-center/themes/types";
import { portalErrorMessage, updateSupportPortal, type SupportPortal } from "./model";

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
  const effectiveScheme = schemes.some(([value]) => value === scheme)
    ? scheme
    : schemes[0][0];

  async function save() {
    setBusy(true);
    setFeedback("");
    try {
      const payload = await updateSupportPortal(portal.id, {
        theme,
        themeScheme: effectiveScheme,
      });
      onChanged(payload.portal);
      setFeedback("Оформление обновлено");
    } catch (caught) {
      setFeedback(portalErrorMessage(caught, "Не удалось сохранить оформление"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="portal-section">
      <div className="portal-section-heading">
        <div>
          <h2>Оформление</h2>
          <p>{selected.description || "Тема публичных страниц портала и её цветовая схема."}</p>
        </div>
      </div>
      <div className="portal-settings-fields">
        <SelectField
          disabled={!canManage}
          label="Тема"
          value={theme}
          onChange={setTheme}
          options={[
            ...themes.map((item): [string, string] => [item.id, item.name]),
            // Тема, которой больше нет в сборке: показываем как есть, чтобы
            // сохранение не подменило её молча.
            ...(known ? [] : [[theme, `${theme} — тема недоступна`] as [string, string]]),
          ]}
        />
        <SelectField
          disabled={!canManage}
          label="Цветовая схема"
          value={effectiveScheme}
          onChange={(value) => setScheme(value as PortalThemeSchemeSetting)}
          options={schemes}
        />
      </div>
      {canManage && (
        <Button variant="secondary" disabled={busy} onClick={() => void save()}>
          Сохранить оформление
        </Button>
      )}
      {feedback && <div className="portal-save-feedback">{feedback}</div>}
    </section>
  );
}
