import type { PortalThemeManifest } from "../types";
import { t } from "../../../../i18n";

export const manifest: PortalThemeManifest = {
  id: "ocean",
  name: "Ocean",
  description: t("portals.soft_oceanic_look_blue_accent"),
  schemes: ["light", "dark"],
  preview: { bg: "#ffffff", ink: "#10283d", accent: "#1b5e8f", radius: "9px" },
};
