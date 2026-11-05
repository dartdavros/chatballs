import { Loader } from "@chatballs/ui";
import type { SiteEventState } from "@chatballs/contracts";
import { t } from "../i18n";
import "./styles.css";

export function ProactiveStatus({ state, autonomous }: { state: SiteEventState | "expired" | null; autonomous?: boolean }) {
  if (state === "pending" || state === "running") return <div className="cb-site-progress" role="status"><Loader size={24} /></div>;
  const key = state === "failed" ? "site_events.failed" : state === "expired" ? "site_events.expired"
    : state === "suppressed" && autonomous === false ? "site_events.unavailable" : null;
  return key ? <p className="cb-site-status" role="status">{t(key)}</p> : null;
}
