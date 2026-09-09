import { useEffect, useState } from "react";

import { Icon } from "../../shared/icons";
import { Button, CopyButton } from "../../shared/ui-controls";
import { shortDate } from "../../shared/utils";
import {
  portalErrorMessage,
  setPortalCustomDomain,
  verifyPortalCustomDomain,
  type SupportPortal,
} from "./model";
import { hostedHost } from "./portalText";
import { t } from "../../i18n";

// Кадр PT5. Подтверждения владения доменом нет: продукт self-hosted, домен и
// установка принадлежат одному владельцу. Остаётся одна A-запись на IP
// установки и техническая проверка «ведёт ли домен сюда» — она нужна для TLS.

export function PortalDomainSettings({
  canManage,
  onChanged,
  portal,
}: {
  canManage: boolean;
  onChanged: (portal: SupportPortal) => void;
  portal: SupportPortal;
}) {
  const [domain, setDomain] = useState(portal.customDomain ?? "");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [failure, setFailure] = useState("");

  useEffect(() => {
    setDomain(portal.customDomain ?? "");
    setFailure("");
  }, [portal.customDomain]);

  const verifiedAt = portal.customDomainVerifiedAt;
  const record = portal.customDomainAddress;

  async function run(action: "save" | "verify") {
    setBusy(true);
    setFeedback("");
    setFailure("");
    try {
      const payload = action === "save"
        ? await setPortalCustomDomain(portal.id, domain.trim())
        : await verifyPortalCustomDomain(portal.id);
      onChanged(payload.portal);
      setFeedback(action === "verify"
        ? t("portals.domain_points_here")
        : domain.trim() ? t("portals.domain_saved_add_record_check") : t("portals.custom_domain_off"));
    } catch (caught) {
      setFailure(portalErrorMessage(
        caught,
        action === "verify" ? t("portals.could_not_check_domain") : t("portals.could_not_save_domain"),
      ));
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    setDomain("");
    setBusy(true);
    setFeedback("");
    setFailure("");
    try {
      const payload = await setPortalCustomDomain(portal.id, "");
      onChanged(payload.portal);
      setFeedback(t("portals.custom_domain_off"));
    } catch (caught) {
      setFailure(portalErrorMessage(caught, t("portals.could_not_turn_domain_off")));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="portal-settings-card">
      <div className="portal-domain-row">
        <label className="portal-field">
          <span className="portal-field-label">{t("portals.domain")}</span>
          <input
            className="is-mono"
            disabled={!canManage}
            placeholder={hostedHost(portal)}
            value={domain}
            onChange={(event) => setDomain(event.target.value.trim().toLocaleLowerCase())}
          />
        </label>
        {portal.customDomain && (
          <span className={`portal-domain-state${verifiedAt ? " is-live" : " is-pending"}`}>
            <Icon name={verifiedAt ? "check" : "clock"} size={14} strokeWidth={2.4} />
            {verifiedAt
              ? t("portals.domain_points_here_checked", { date: shortDate(verifiedAt) })
              : t("portals.domain_has_not_been_checked")}
          </span>
        )}
      </div>

      {portal.customDomain && (
        <div>
          <div className="portal-dns-head">
            <strong>{t("portals.record_at_domain_registrar")}</strong>
            <span>{t("portals.dns_update_takes_up_24")}</span>
          </div>
          <table className="portal-dns-table">
            <thead>
              <tr><th>{t("portals.type")}</th><th>{t("portals.name")}</th><th>{t("portals.value")}</th><th /></tr>
            </thead>
            <tbody>
              {record ? (
                <tr>
                  <td className="portal-dns-type">{record.type}</td>
                  <td><code>{record.name}</code></td>
                  <td><code>{t("portals.ip_of_installation", { value: record.value })}</code></td>
                  <td><CopyButton className="portal-dns-copy" label="" value={record.value} /></td>
                </tr>
              ) : (
                <tr>
                  <td className="portal-dns-type">A</td>
                  <td><code>{portal.customDomain}</code></td>
                  <td><code>{t("portals.administrator_has_not_set_installation")}</code></td>
                  <td />
                </tr>
              )}
            </tbody>
          </table>
          <p className="portal-dns-note">
            {t("portals.domain_no_extra_setup")}
          </p>
        </div>
      )}

      {canManage && (
        <div className="portal-settings-actions">
          <Button variant="primary" disabled={busy} onClick={() => void run("save")}>{t("portals.save_domain")}</Button>
          <Button variant="secondary" disabled={busy || !portal.customDomain} onClick={() => void run("verify")}>{t("portals.check_dns")}</Button>
          <span className="portal-settings-gap" />
          {portal.customDomain && (
            <Button variant="danger-outline" disabled={busy} onClick={() => void disconnect()}>{t("portals.turn_domain_off")}</Button>
          )}
        </div>
      )}
      {feedback && <span className="portal-settings-note">{feedback}</span>}
      {failure && <div className="portal-form-error">{failure}</div>}
    </div>
  );
}
