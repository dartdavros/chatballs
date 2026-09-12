import { useState } from "react";

import { DecisionDialog } from "../../shared/DecisionDialog";
import { Icon, LogoSpinner } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { installUpdate } from "./api";
import { useUpdateInfo } from "./useUpdateInfo";
import { t } from "../../i18n";

// Полоса поверх рабочей области у администратора установки: есть новая
// версия, идёт установка, установка завершена или сорвалась. Та же полоса,
// что у установки демо-данных (ADR-CHATBALLS-0049).

export function UpdateBanner({ enabled }: { enabled: boolean }) {
  const { info, setInfo, installing, unreachable, finished } = useUpdateInfo(enabled);
  const [dismissed, setDismissed] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [errorText, setErrorText] = useState("");

  if (!enabled) return null;

  async function install() {
    setBusy(true);
    setErrorText("");
    try {
      setInfo(await installUpdate());
      setConfirming(false);
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : t("common.could_not_complete_action"));
    } finally {
      setBusy(false);
    }
  }

  const version = info?.install.version ?? info?.latestVersion ?? "";

  if (installing) {
    const stage = unreachable ? "restarting" : info?.install.message || "starting";
    const stageKey = (["downloading", "pulling", "restarting"].includes(stage) ? stage : "starting") as "downloading" | "pulling" | "restarting" | "starting";
    return (
      <div className="demo-install-banner update-banner">
        <LogoSpinner size={17} />
        <span>{t("updates.installing", { version })} {t(`updates.stage_${stageKey}`)}</span>
      </div>
    );
  }

  if (finished && info?.install.status === "DONE" && dismissed !== `done:${version}`) {
    return (
      <div className="demo-install-banner update-banner is-done">
        <Icon name="check" size={15} strokeWidth={2.2} />
        <span>{t("updates.done", { version })}</span>
        <button type="button" onClick={() => window.location.reload()}>{t("common.show")}</button>
        <button className="demo-install-close" type="button" onClick={() => setDismissed(`done:${version}`)} aria-label={t("common.hide")}>
          <Icon name="close" size={14} strokeWidth={2} />
        </button>
      </div>
    );
  }

  if (info?.install.status === "FAILED" && dismissed !== `failed:${version}`) {
    return (
      <div className="demo-install-banner update-banner is-failed">
        <Icon name="warning" size={15} strokeWidth={2} />
        <span>{t("updates.failed", { version })}{info.install.message ? `: ${info.install.message}` : ""}</span>
        <button className="demo-install-close" type="button" onClick={() => setDismissed(`failed:${version}`)} aria-label={t("common.hide")}>
          <Icon name="close" size={14} strokeWidth={2} />
        </button>
      </div>
    );
  }

  if (!info?.available || dismissed === `available:${info.latestVersion}`) return null;

  return (
    <>
      <div className="demo-install-banner update-banner">
        <Icon name="download" size={15} strokeWidth={2} />
        <span>
          {t("updates.available_title", { version: info.latestVersion ?? "" })}
          {!info.updaterOnline && ` · ${t("updates.updater_offline")}`}
        </span>
        {info.latestPageUrl && (
          <a className="link is-neutral" href={info.latestPageUrl} target="_blank" rel="noreferrer">{t("updates.whats_new")}</a>
        )}
        <button type="button" disabled={!info.updaterOnline} onClick={() => setConfirming(true)}>{t("updates.install")}</button>
        <button className="demo-install-close" type="button" onClick={() => setDismissed(`available:${info.latestVersion}`)} aria-label={t("common.hide")}>
          <Icon name="close" size={14} strokeWidth={2} />
        </button>
      </div>
      <DecisionDialog
        open={confirming}
        tone="warning"
        icon="download"
        title={t("updates.confirm_title", { version: info.latestVersion ?? "" })}
        description={errorText || t("updates.confirm_text")}
        onClose={() => setConfirming(false)}
        actions={(
          <>
            <Button variant="secondary" disabled={busy} onClick={() => setConfirming(false)}>{t("common.cancel")}</Button>
            <Button variant="primary" disabled={busy} onClick={() => void install()}>{t("updates.install")}</Button>
          </>
        )}
      />
    </>
  );
}
