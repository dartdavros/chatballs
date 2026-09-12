import { useState } from "react";

import { Button } from "../../shared/ui-controls";
import { shortDateTime } from "../../shared/utils";
import { checkUpdates, installUpdate } from "./api";
import { useUpdateInfo } from "./useUpdateInfo";
import { t } from "../../i18n";

// Карточка «Обновления» в разделе «Платформа»: версия установки, последняя
// версия на канале релизов, проверка и установка по кнопке. Сама установка
// идёт снаружи приложения (ADR-CHATBALLS-0049), здесь только её состояние.

export function UpdatesCard({ canManage }: { canManage: boolean }) {
  const { info, setInfo, installing, unreachable } = useUpdateInfo(true);
  const [busy, setBusy] = useState(false);
  const [errorText, setErrorText] = useState("");

  async function run(action: () => Promise<typeof info>) {
    setBusy(true);
    setErrorText("");
    try {
      const next = await action();
      if (next) setInfo(next);
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : t("common.could_not_complete_action"));
    } finally {
      setBusy(false);
    }
  }

  if (!info && !unreachable) return null;

  const latest = info?.latestVersion;
  const checked = info?.checkedAt ? t("updates.checked_at", { time: shortDateTime(info.checkedAt) }) : t("updates.never_checked");
  const status = info?.install.status;

  return (
    <div className="administration-card">
      <div className="settings-card-head">
        <div>
          <strong>{t("updates.card_title")}</strong>
          <small>{t("updates.card_hint")}</small>
        </div>
        {canManage && (
          <Button variant="secondary" disabled={busy || installing} onClick={() => void run(checkUpdates)}>{t("updates.check")}</Button>
        )}
      </div>
      <dl className="settings-facts">
        <div><dt>{t("updates.current_version")}</dt><dd>{info?.currentVersion ?? "—"}</dd></div>
        <div>
          <dt>{t("updates.latest_version")}</dt>
          <dd>
            {latest ?? "—"}
            {latest && info?.latestPageUrl && (
              <> · <a className="link is-neutral" href={info.latestPageUrl} target="_blank" rel="noreferrer">{t("updates.whats_new")}</a></>
            )}
          </dd>
        </div>
        <div><dt>{t("updates.checked")}</dt><dd>{checked}</dd></div>
      </dl>
      {info?.checkError && <div className="settings-section-error">{t("updates.check_error", { error: info.checkError })}</div>}
      {errorText && <div className="settings-section-error">{errorText}</div>}
      {installing && (
        <p className="settings-card-note">{t("updates.installing", { version: info?.install.version ?? latest ?? "" })} {t(`updates.stage_${unreachable ? "restarting" : (["downloading", "pulling", "restarting"].includes(info?.install.message ?? "") ? info?.install.message : "starting") as "downloading" | "pulling" | "restarting" | "starting"}`)}</p>
      )}
      {!installing && status === "FAILED" && info?.install.version && (
        <div className="settings-section-error">{t("updates.failed", { version: info.install.version })}{info.install.message ? `: ${info.install.message}` : ""}</div>
      )}
      {!installing && info?.available && (
        <div className="settings-card-actions">
          {canManage
            ? <Button variant="primary" disabled={busy || !info.updaterOnline} onClick={() => void run(installUpdate)}>{t("updates.install_version", { version: latest ?? "" })}</Button>
            : <span className="settings-card-note">{t("updates.available_title", { version: latest ?? "" })}</span>}
          {!info.updaterOnline && <span className="settings-card-note">{t("updates.updater_offline")}</span>}
        </div>
      )}
      {!installing && info && !info.available && latest && !info.checkError && (
        <p className="settings-card-note">{t("updates.up_to_date")}</p>
      )}
    </div>
  );
}
