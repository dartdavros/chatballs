import { useEffect, useState } from "react";

import { FormField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import {
  portalErrorMessage,
  setPortalCustomDomain,
  verifyPortalCustomDomain,
  type SupportPortal,
} from "./model";

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

  useEffect(() => setDomain(portal.customDomain ?? ""), [portal.customDomain]);

  async function save() {
    setBusy(true);
    setFeedback("");
    try {
      const payload = await setPortalCustomDomain(portal.id, domain);
      onChanged(payload.portal);
      setFeedback(domain.trim() ? "Домен сохранён. Добавьте показанные DNS-записи и проверьте домен." : "Свой домен отключён");
    } catch (error) {
      setFeedback(portalErrorMessage(error, "Не удалось сохранить домен"));
    } finally {
      setBusy(false);
    }
  }

  async function verify() {
    setBusy(true);
    setFeedback("");
    try {
      const payload = await verifyPortalCustomDomain(portal.id);
      onChanged(payload.portal);
      setFeedback("Домен подтверждён");
    } catch (error) {
      setFeedback(portalErrorMessage(error, "Не удалось подтвердить домен"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="portal-section">
      <div className="portal-section-heading">
        <div><h2>Свой домен</h2><p>Подключите адрес вашей компании к опубликованному порталу.</p></div>
      </div>
      <div className="portal-settings-fields">
        <FormField
          disabled={!canManage}
          label="Домен"
          placeholder="help.example.com"
          value={domain}
          onChange={canManage ? setDomain : undefined}
          mono
          wide
        />
      </div>
      {(portal.customDomainAddress || portal.customDomainVerification) && (
        <div className="portal-domain-verification">
          <strong>DNS-записи для {portal.customDomain}</strong>
          {portal.customDomainAddress && (
            <div className="portal-domain-record">
              <b>A-запись</b>
              <dl>
                <div><dt>Тип</dt><dd>{portal.customDomainAddress.type}</dd></div>
                <div><dt>Имя</dt><dd><code>{portal.customDomainAddress.name}</code></dd></div>
                <div><dt>Значение</dt><dd><code>{portal.customDomainAddress.value}</code></dd></div>
              </dl>
            </div>
          )}
          {portal.customDomainVerification && (
            <div className="portal-domain-record">
              <b>TXT-запись</b>
              <dl>
                <div><dt>Тип</dt><dd>{portal.customDomainVerification.type}</dd></div>
                <div><dt>Имя</dt><dd><code>{portal.customDomainVerification.name}</code></dd></div>
                <div><dt>Значение</dt><dd><code>{portal.customDomainVerification.value}</code></dd></div>
              </dl>
            </div>
          )}
        </div>
      )}
      <div className="portal-domain-actions">
        {canManage && <Button variant="secondary" disabled={busy} onClick={() => void save()}>Сохранить домен</Button>}
        {canManage && portal.customDomainVerification && <Button variant="primary" disabled={busy} onClick={() => void verify()}>Проверить DNS</Button>}
      </div>
      {feedback && <div className="portal-save-feedback">{feedback}</div>}
    </section>
  );
}
