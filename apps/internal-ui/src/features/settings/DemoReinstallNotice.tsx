import { t } from "../../i18n";
import { LogoSpinner } from "../../shared/icons";
import type { DemoState } from "./useDemoData";
import "./demo-reinstall.css";

export function DemoReinstallNotice({ reinstall }: { reinstall: DemoState["reinstall"] }) {
  const status = reinstall?.status;
  const title = status === "RUNNING" ? t("settings.demo_reinstall_running")
    : status === "SUCCEEDED" ? t("settings.demo_reinstall_succeeded")
      : t("settings.demo_reinstall_failed");
  const detail = status === "RUNNING" ? t("settings.demo_reinstall_preparing")
    : status === "SUCCEEDED" ? t("settings.demo_reinstall_repeat")
      : failureDetail(reinstall?.errorCode);

  return (
    <div className="settings-demo-operation" aria-live="polite">
      {status && (
        <div className={`settings-demo-notice is-${status.toLowerCase()}`}>
          {status === "RUNNING" && <LogoSpinner size={22} />}
          <div>
            <strong>{title}</strong>
            <p>{detail}</p>
          </div>
        </div>
      )}
    </div>
  );
}

function failureDetail(code?: string) {
  switch (code) {
    case "WORKING_CONVERSATION":
      return t("settings.demo_reinstall_conflict_conversation");
    case "WORKING_REFERENCE":
      return t("settings.demo_reinstall_conflict");
    default:
      return t("settings.demo_reinstall_retry");
  }
}
