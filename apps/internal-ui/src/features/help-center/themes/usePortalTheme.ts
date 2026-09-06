import { useEffect, useState } from "react";

import "./contract.css";
import {
  loadPortalThemeStyles,
  resolvePortalScheme,
  resolvePortalTheme,
} from "./registry";
import type { PortalThemeSchemeSetting } from "./types";

const DARK_MEDIA = "(prefers-color-scheme: dark)";

/**
 * Применяет тему портала к документу Help Center: грузит CSS темы, ставит
 * data-portal-theme и data-theme на <html> (тот же атрибут схемы, что и у
 * хаба — shared/appearance.ts). Возвращает готовность: до неё страница
 * держит boot-загрузчик, чтобы не мигать чужим оформлением.
 */
export function usePortalTheme(
  theme: string | null,
  schemeSetting: PortalThemeSchemeSetting,
): boolean {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (theme === null) return;
    let active = true;
    const manifest = resolvePortalTheme(theme);
    const media = window.matchMedia ? window.matchMedia(DARK_MEDIA) : null;
    const root = document.documentElement;
    const applyScheme = () => {
      const scheme = resolvePortalScheme(
        manifest,
        schemeSetting,
        Boolean(media?.matches),
      );
      root.dataset.theme = scheme;
      root.style.setProperty("color-scheme", scheme);
    };

    applyScheme();
    media?.addEventListener("change", applyScheme);
    loadPortalThemeStyles(manifest.id)
      .catch(() => undefined)
      .then(() => {
        if (!active) return;
        root.dataset.portalTheme = manifest.id;
        applyScheme();
        setReady(true);
      });

    return () => {
      active = false;
      media?.removeEventListener("change", applyScheme);
    };
  }, [theme, schemeSetting]);

  return ready;
}
