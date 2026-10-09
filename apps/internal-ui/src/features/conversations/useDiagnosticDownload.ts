import { useRef, useState } from "react";
import { downloadDiagnostic } from "./downloadDiagnostic";
import { t } from "../../i18n";

export function useDiagnosticDownload(conversationId: number, onError: (error: string) => void) {
  const [downloading, setDownloading] = useState(false);
  const currentId = useRef(conversationId);
  currentId.current = conversationId;
  async function download() {
    if (downloading) return;
    setDownloading(true);
    onError("");
    try { await downloadDiagnostic(conversationId); }
    catch (error) {
      if (currentId.current === conversationId) {
        onError(error instanceof Error ? error.message : t("diagnostics.download_failed"));
      }
    } finally { setDownloading(false); }
  }
  return { downloading, download };
}
