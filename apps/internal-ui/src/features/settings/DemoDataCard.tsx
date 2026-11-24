import { Modal } from "antd";
import { useState } from "react";

import { fmt, t } from "../../i18n";
import { Button } from "../../shared/ui-controls";
import { shortDate } from "../../shared/utils";
import { DemoAccounts } from "./DemoAccounts";
import { DemoReinstallNotice } from "./DemoReinstallNotice";
import { useDemoData, type DemoState } from "./useDemoData";

export function demoStatusLabel(state: DemoState): string {
  switch (state.status) {
    case "INSTALLED":
    case "REINSTALLING":
      return t("settings.installed");
    case "INSTALLING":
      return t("settings.installing");
    case "REMOVING":
      return t("settings.removing");
    case "FAILED":
      return t("settings.installation_failed");
    default:
      return t("settings.not_installed");
  }
}

export function DemoDataCard({ reload }: { reload: () => void }) {
  const { state, busy, error, submitting, submit } = useDemoData(reload);
  const [confirmation, setConfirmation] = useState<"remove" | "reinstall" | null>(null);
  const installed = state?.status === "INSTALLED" || state?.status === "REINSTALLING";
  const northWind = state?.northWind || !installed;
  const reinstall = confirmation === "reinstall";

  async function confirm() {
    if (confirmation && await submit(confirmation)) setConfirmation(null);
  }

  return (
    <div className="administration-card">
      <div className="settings-demo-head">
        <div className="settings-demo-title">
          <strong>{t(northWind ? "settings.demo_north_wind" : "settings.demo_data")}</strong>
          {state && <b className={`settings-demo-status is-${installed ? "installed" : state.status.toLowerCase()}`}>{demoStatusLabel(state)}</b>}
          {installed && state && (
            <small>
              {t("settings.demo_records_count", { count: fmt.number(state.recordsCount) })}
              {state.finishedAt ? ` · ${shortDate(state.finishedAt)}` : ""}
            </small>
          )}
        </div>
        <div className="settings-demo-actions">
          {!installed && (
            <Button variant="primary" disabled={busy || submitting || state === null} onClick={() => void submit("install")}>
              {state?.status === "INSTALLING" ? t("settings.installing_2") : state?.status === "FAILED" ? t("settings.install_again") : t("settings.install")}
            </Button>
          )}
          {installed && (
            <Button variant="secondary" disabled={busy || submitting} onClick={() => setConfirmation("reinstall")}>
              {t("settings.demo_reinstall")}
            </Button>
          )}
          {(installed || state?.status === "REMOVING") && (
            <Button variant="danger-outline" disabled={busy || submitting} onClick={() => setConfirmation("remove")}>
              {state?.status === "REMOVING" ? t("settings.removing_2") : t("settings.remove_demo_data")}
            </Button>
          )}
        </div>
      </div>
      <p className="settings-section-note">
        {t(northWind ? "settings.demo_north_wind_contents" : "settings.demo_contents")}
      </p>
      {installed && state && <DemoReinstallNotice reinstall={state.reinstall} />}
      {installed && state && <DemoAccounts accounts={state.accounts} />}
      {state?.error && <div className="settings-section-error">{state.error}</div>}
      {error && !confirmation && <div className="settings-section-error">{error}</div>}
      {confirmation && (
        <Modal open title={t(reinstall ? "settings.demo_reinstall_title" : "settings.remove_demo_data_2")}
          onCancel={submitting ? undefined : () => setConfirmation(null)}
          closable={!submitting} maskClosable={!submitting} keyboard={!submitting} footer={null} destroyOnHidden>
          <div className="integration-form">
            <p>{t(reinstall ? "settings.demo_reinstall_description" : "settings.every_record_demo_set_will")}</p>
            {error && <div className="integration-form-error">{error}</div>}
            <div className="integration-form-actions">
              <Button variant="secondary" disabled={submitting} onClick={() => setConfirmation(null)}>{t("common.cancel")}</Button>
              <Button variant="danger-outline" disabled={busy || submitting} onClick={() => void confirm()}>
                {t(reinstall ? "settings.demo_reinstall" : "common.delete")}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
