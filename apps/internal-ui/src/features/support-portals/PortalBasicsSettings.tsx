import { useEffect, useState } from "react";

import { Icon } from "../../shared/icons";
import { Button, CopyButton } from "../../shared/ui-controls";
import {
  portalErrorMessage,
  portalFieldErrors,
  updateSupportPortal,
  type PortalAddressConfig,
  type SupportPortal,
} from "./model";
import { LOCALE_OPTIONS } from "./portalText";

// Кадр PT4: имя, ключ портала на этой установке и язык. Базовый домен —
// из ответа API (`address.baseDomain`), в UI он никогда не зашивается.

export function PortalBasicsSettings({
  address,
  canManage,
  portal,
  onChanged,
}: {
  address: PortalAddressConfig;
  canManage: boolean;
  portal: SupportPortal;
  onChanged: (portal: SupportPortal) => void;
}) {
  const [name, setName] = useState(portal.name);
  const [slug, setSlug] = useState(portal.slug);
  const [locale, setLocale] = useState(portal.defaultLocale);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    setName(portal.name);
    setSlug(portal.slug);
    setLocale(portal.defaultLocale);
  }, [portal]);

  const port = address.port ? `:${address.port}` : "";
  const finalUrl = `${address.scheme}://${slug || portal.slug}.${address.baseDomain}${port}/`;

  async function save() {
    setBusy(true);
    setFeedback("");
    setFieldErrors({});
    try {
      const payload = await updateSupportPortal(portal.id, { name, slug, defaultLocale: locale });
      onChanged(payload.portal);
      setFeedback("Настройки сохранены");
    } catch (caught) {
      setFieldErrors(portalFieldErrors(caught));
      setFeedback(portalErrorMessage(caught, "Не удалось сохранить настройки"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="portal-settings-card">
      <label className="portal-field">
        <span className="portal-field-label">Название портала</span>
        <input
          disabled={!canManage}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <small>Показывается в шапке публичных страниц и в заголовке браузера.</small>
        {fieldErrors.name && <small className="portal-field-error">{fieldErrors.name}</small>}
      </label>

      <div className="portal-field">
        <span className="portal-field-label">Адрес на этой установке</span>
        <span className="portal-key-input">
          <input
            disabled={!canManage}
            maxLength={63}
            value={slug}
            onChange={(event) => setSlug(event.target.value.toLocaleLowerCase())}
          />
          <b>.{address.baseDomain}</b>
        </span>
        <small>
          Строчные латинские буквы, цифры и дефис. Базовый домен <b>{address.baseDomain}</b> задан
          администратором при установке и одинаков для всех порталов этой инсталляции. Адрес входит
          в ссылки на статьи — после смены старые ссылки перестанут работать.
        </small>
        {fieldErrors.slug && <small className="portal-field-error">{fieldErrors.slug}</small>}
      </div>

      <label className="portal-field is-narrow">
        <span className="portal-field-label">Основной язык</span>
        <span className="portal-select">
          <select disabled={!canManage} value={locale} onChange={(event) => setLocale(event.target.value)}>
            {LOCALE_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
          <Icon name="chevron" size={14} strokeWidth={2} />
        </span>
        <small>Язык, который подставляется новым статьям. Статьи на других языках остаются как есть.</small>
      </label>

      <div className="portal-final-link">
        <span>
          <small>Итоговая ссылка</small>
          <code>{finalUrl}</code>
        </span>
        <CopyButton className="portal-inline-button" label="Копировать" value={finalUrl} />
        <a className="portal-inline-button is-accent" href={finalUrl} rel="noreferrer" target="_blank">
          <Icon name="external" size={13} strokeWidth={2} />Открыть
        </a>
      </div>

      {canManage && (
        <div className="portal-settings-actions">
          <Button variant="primary" disabled={busy} onClick={() => void save()}>Сохранить настройки</Button>
          {feedback && <span className="portal-settings-note">{feedback}</span>}
        </div>
      )}
    </div>
  );
}
