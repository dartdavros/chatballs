import { useEffect, useState } from "react";

import { FormField, SelectField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import type { Product } from "../../types";
import {
  listPortalSupportChannels,
  portalErrorMessage,
  updateSupportPortal,
  type PortalWidgetOption,
  type SupportPortal,
} from "./model";
import { PortalDomainSettings } from "./PortalDomainSettings";
import { PortalProductSettings } from "./PortalProductSettings";
import { PortalWidgetSettings } from "./PortalWidgetSettings";

export function PortalSettings({
  portal,
  products,
  canManage,
  onChanged,
}: {
  portal: SupportPortal;
  products: Product[];
  canManage: boolean;
  onChanged: (portal: SupportPortal) => void;
}) {
  const [name, setName] = useState(portal.name);
  const [slug, setSlug] = useState(portal.slug);
  const [locale, setLocale] = useState(portal.defaultLocale);
  const [supportWidgets, setSupportWidgets] = useState<PortalWidgetOption[]>([]);
  const [anonymousWidgets, setAnonymousWidgets] = useState<PortalWidgetOption[]>([]);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    setName(portal.name);
    setSlug(portal.slug);
    setLocale(portal.defaultLocale);
  }, [portal]);

  useEffect(() => {
    listPortalSupportChannels(portal.id)
      .then((payload) => {
        setSupportWidgets(payload.items);
        setAnonymousWidgets(payload.widgetItems);
      })
      .catch(() => {
        setSupportWidgets([]);
        setAnonymousWidgets([]);
      });
  }, [portal.id]);

  async function saveBasics() {
    setBusy(true);
    setFeedback("");
    try {
      const payload = await updateSupportPortal(portal.id, {
        name,
        slug,
        defaultLocale: locale,
      });
      onChanged(payload.portal);
      setFeedback("Настройки сохранены");
    } catch (caught) {
      setFeedback(portalErrorMessage(caught, "Не удалось сохранить настройки"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="portal-settings-grid">
      <section className="portal-section">
        <div className="portal-section-heading">
          <div><h2>Основные настройки</h2><p>Название, публичный адрес и язык материалов.</p></div>
        </div>
        <div className="portal-settings-fields">
          <FormField disabled={!canManage} label="Название портала" value={name} onChange={canManage ? setName : undefined} wide />
          <FormField disabled={!canManage} label="Адрес портала" value={slug} onChange={canManage ? setSlug : undefined} mono wide />
          <p className="portal-address-preview">{portal.publicUrl}</p>
          <SelectField
            disabled={!canManage}
            label="Язык по умолчанию"
            value={locale}
            onChange={setLocale}
            options={[["ru", "Русский"], ["en", "English"]]}
          />
        </div>
        {canManage && <Button variant="primary" disabled={busy} onClick={() => void saveBasics()}>Сохранить настройки</Button>}
      </section>

      <PortalProductSettings
        canManage={canManage}
        widgets={supportWidgets}
        portal={portal}
        products={products}
        onChanged={onChanged}
      />
      <PortalWidgetSettings
        canManage={canManage}
        widgets={anonymousWidgets}
        portal={portal}
        onChanged={onChanged}
      />
      <PortalDomainSettings portal={portal} canManage={canManage} onChanged={onChanged} />
      {feedback && <div className="portal-save-feedback">{feedback}</div>}
    </div>
  );
}
