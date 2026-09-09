import type { PortalThemeManifest } from "../types";
import { t } from "../../../../i18n";

export const manifest: PortalThemeManifest = {
  id: "classic",
  name: t("portals.classic"),
  description: t("portals.base_help_center_look_light"),
  schemes: ["light", "dark"],
  preview: { bg: "#ffffff", ink: "#1f1f1f", accent: "#1f1f1f", radius: "5px" },
};
