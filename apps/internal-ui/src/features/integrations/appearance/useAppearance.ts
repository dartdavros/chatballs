import { useState } from "react";

import { api } from "../../../api/client";
import { t } from "../../../i18n";
import type { Integration } from "../model";
import { appearanceConfig, COLOR_PRESETS, readAppearance, validHex, type WidgetAppearance } from "./model";

export function useAppearance(integration: Integration, onSaved: (integration: Integration) => void) {
  const initial = readAppearance(integration.config);
  const [appearance, setAppearance] = useState(initial);
  const [saved, setSaved] = useState(initial);
  const [custom, setCustom] = useState(!COLOR_PRESETS.some(({ hex }) => hex === initial.accent.toLowerCase()));
  const [customHex, setCustomHex] = useState(custom ? initial.accent : "");
  const [busy, setBusy] = useState(false);
  const [uploads, setUploads] = useState<Record<string, boolean>>({});
  const [error, setError] = useState("");
  const dirty = JSON.stringify(appearance) !== JSON.stringify(saved) || (custom && !validHex(customHex));
  const uploading = Object.values(uploads).some(Boolean);
  const change = (patch: Partial<WidgetAppearance>) => setAppearance((previous) => ({ ...previous, ...patch }));

  function pickPreset(accent: string) {
    setCustom(false);
    change({ accent });
  }

  function changeHex(hex: string) {
    setCustom(true);
    setCustomHex(hex.trim());
    // W3 использует «Терракоту», пока свой HEX некорректен. Сервер принимает
    // только #RRGGBB: этот же цвет сохраняется, не блокируя остальные настройки.
    change({ accent: validHex(hex.trim()) ? hex.trim().toLowerCase() : COLOR_PRESETS[4].hex });
  }

  async function save() {
    setBusy(true);
    setError("");
    try {
      const { integration: updated } = await api<{ integration: Integration }>(`/api/v1/integrations/${integration.id}/`, {
        method: "PATCH", body: JSON.stringify({ config: appearanceConfig(integration.config, appearance) }),
      });
      const normalized = readAppearance(updated.config);
      setSaved(normalized);
      // Не перезаписывать изменения, внесённые во время запроса сохранения.
      setAppearance((current) => JSON.stringify(current) === JSON.stringify(appearance) ? normalized : current);
      onSaved(updated);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("common.could_not_save"));
    } finally {
      setBusy(false);
    }
  }

  return {
    appearance, custom, customHex, dirty, busy: busy || uploading, error, change, pickPreset, changeHex, save,
    launcherPreviewCss: appearance.customCss === saved.customCss ? saved.launcherCss ?? "" : "",
    uploadBusy: (key: string, value: boolean) => setUploads((current) => ({ ...current, [key]: value })),
  };
}
