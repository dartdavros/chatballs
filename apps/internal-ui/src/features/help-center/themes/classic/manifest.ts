import type { PortalThemeManifest } from "../types";

export const manifest: PortalThemeManifest = {
  id: "classic",
  name: "Классическая",
  description: "Базовое оформление Help Center: светлая подложка, чернильный акцент.",
  schemes: ["light", "dark"],
  preview: { bg: "#ffffff", ink: "#1f1f1f", accent: "#1f1f1f", radius: "5px" },
};
