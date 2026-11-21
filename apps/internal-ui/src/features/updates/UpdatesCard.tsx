import { useState } from "react";

import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { shortDateTime } from "../../shared/utils";
import type { InstancePayload } from "../settings/instance";
import { checkUpdates, installUpdate } from "./api";
import { useUpdatesCardPresence } from "./cardPresence";
import { ExternalChecksPanel } from "./ExternalChecksPanel";
import { UpdateProgress } from "./UpdateProgress";
import { useShellExternalChecks } from "./useExternalChecks";
import { useUpdateInfo } from "./useUpdateInfo";
import { t } from "../../i18n";

// Карточка «Обновления» в разделе «Платформа»: версия установки, последняя
// версия на канале релизов, проверка и установка по кнопке. Сама установка
// идёт снаружи приложения (ADR-CHATBALLS-0049), здесь только её состояние —
// но состояние подробное: обновление перезапускает сервисы, и всё это время
// человек должен видеть, что идёт и на каком оно шаге.

export function UpdatesCard({ canManage, externalChecksEnabled, onSettingsSaved }: {
  canManage: boolean;
  externalChecksEnabled: boolean;
  onSettingsSaved: (settings: InstancePayload) => void;
}) {
  const { info, setInfo, installing, unreachable, finished, forget, markPending, targetVersion, startedAt } =
    useUpdateInfo(true);
  const external = useShellExternalChecks();
  const enabled = external.enabled ?? externalChecksEnabled;
  const [busy, setBusy] = useState(false);
  const [errorText, setErrorText] = useState("");
  // Пока карточка на экране, полоса наверху о том же не говорит.
  useUpdatesCardPresence();

  async function toggleExternalChecks() {
    const settings = await external.toggle(!enabled);
    if (settings) onSettingsSaved(settings);
  }

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

  function install() {
    // Прогресс появляется по нажатию, а не по ответу сервера: запрос на
    // установку идёт секунду, и всё это время экран не должен молчать.
    markPending(info?.latestVersion ?? null);
    void run(installUpdate);
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
          <Button variant="secondary" disabled={busy || installing || external.saving || !enabled} onClick={() => void run(checkUpdates)}>{t("updates.check")}</Button>
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
        <UpdateProgress
          info={info}
          unreachable={unreachable}
          version={targetVersion ?? latest ?? ""}
          startedAt={startedAt}
        />
      )}
      {finished && (
        <div className="update-done" role="status">
          <Icon name="check" size={15} strokeWidth={2.2} />
          <div>
            <strong>{t("updates.done_title", { version: info?.currentVersion ?? targetVersion ?? "" })}</strong>
            <small>{t("updates.done_hint")}</small>
          </div>
          <Button variant="primary" onClick={() => window.location.reload()}>{t("updates.reload")}</Button>
          <Button variant="secondary" onClick={forget}>{t("common.hide")}</Button>
        </div>
      )}
      {!installing && status === "FAILED" && info?.install.version && (
        <div className="settings-section-error">{t("updates.failed", { version: info.install.version })}{info.install.message ? `: ${info.install.message}` : ""}</div>
      )}
      {!installing && !finished && info?.available && (
        <div className="settings-card-actions">
          {canManage
            ? <Button variant="primary" disabled={busy || !info.updaterOnline} onClick={install}>{t("updates.install_version", { version: latest ?? "" })}</Button>
            : <span className="settings-card-note">{t("updates.available_title", { version: latest ?? "" })}</span>}
          {!info.updaterOnline && <span className="settings-card-note">{t("updates.updater_offline")}</span>}
        </div>
      )}
      {!installing && !finished && info && !info.available && latest && !info.checkError && (
        <p className="settings-card-note">{t("updates.up_to_date")}</p>
      )}
      {canManage && (
        <ExternalChecksPanel
          enabled={enabled}
          saving={external.saving}
          saveFailed={external.saveFailed}
          onToggle={() => void toggleExternalChecks()}
        />
      )}
    </div>
  );
}
