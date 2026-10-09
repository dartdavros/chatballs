import type { diagnosticsRu } from "./diagnostics.ru";

export const diagnosticsEn: Record<keyof typeof diagnosticsRu, string> = {
  "diagnostics.download": "Download diagnostics",
  "diagnostics.download_failed": "Could not download diagnostics",
};
