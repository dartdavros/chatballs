import type { WebConfig } from "./api";

export type WidgetAppearance = {
  accent?: string;
  theme?: "light" | "dark";
  launcherIcon?: string;
  headerIcon?: string | null;
  launcherPosition?: "left" | "right";
  launcherSize?: 48 | 56 | 64;
  launcherShape?: "circle" | "rounded" | "square";
  customCss?: string;
};

export function resolveWidgetAppearance(config: WebConfig | null) {
  const appearance = config?.appearance;
  return {
    accent: appearance?.accent || config?.accent || "#1677ff",
    theme: appearance?.theme === "dark" ? "dark" : "light",
    headerIcon: appearance?.headerIcon === null
      ? null
      : appearance?.headerIcon || appearance?.launcherIcon || "",
    customCss: appearance?.customCss || "",
  };
}
