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
        ? "Домен ведёт сюда"
        : domain.trim() ? "Домен сохранён. Добавьте A-запись и проверьте DNS." : "Свой домен отключён");
    } catch (caught) {
      setFailure(portalErrorMessage(
        caught,
        action === "verify" ? "Не удалось проверить домен" : "Не удалось сохранить домен",
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
      setFeedback("Свой домен отключён");
    } catch (caught) {
      setFailure(portalErrorMessage(caught, "Не удалось отключить домен"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="portal-settings-card">
      <div className="portal-domain-row">
        <label className="portal-field">
          <span className="portal-field-label">Домен</span>
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
              ? `Домен ведёт сюда · проверено ${shortDate(verifiedAt)}`
              : "Домен ещё не проверялся"}
          </span>
        )}
      </div>

      {portal.customDomain && (
        <div>
          <div className="portal-dns-head">
            <strong>Запись у регистратора домена</strong>
            <span>обновление DNS занимает до 24 часов</span>
          </div>
          <table className="portal-dns-table">
            <thead>
              <tr><th>ТИП</th><th>ИМЯ</th><th>ЗНАЧЕНИЕ</th><th /></tr>
            </thead>
            <tbody>
              {record ? (
                <tr>
                  <td className="portal-dns-type">{record.type}</td>
                  <td><code>{record.name}</code></td>
                  <td><code>{record.value} · IP этой установки</code></td>
                  <td><CopyButton className="portal-dns-copy" label="" value={record.value} /></td>
                </tr>
              ) : (
                <tr>
                  <td className="portal-dns-type">A</td>
                  <td><code>{portal.customDomain}</code></td>
                  <td><code>IP этой установки не задан администратором</code></td>
                  <td />
                </tr>
              )}
            </tbody>
          </table>
          <p className="portal-dns-note">
            Больше ничего добавлять не нужно: домен ваш, установка ваша — проверка лишь смотрит,
            ведёт ли запись на этот сервер, и выписывает сертификат.
          </p>
        </div>
      )}

      {canManage && (
        <div className="portal-settings-actions">
          <Button variant="primary" disabled={busy} onClick={() => void run("save")}>Сохранить домен</Button>
          <Button variant="secondary" disabled={busy || !portal.customDomain} onClick={() => void run("verify")}>Проверить DNS</Button>
          <span className="portal-settings-gap" />
          {portal.customDomain && (
            <Button variant="danger-outline" disabled={busy} onClick={() => void disconnect()}>Отключить домен</Button>
          )}
        </div>
      )}
      {feedback && <span className="portal-settings-note">{feedback}</span>}
      {failure && <div className="portal-form-error">{failure}</div>}
    </div>
  );
}
