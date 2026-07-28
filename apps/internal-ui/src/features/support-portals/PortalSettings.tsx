import { useEffect, useMemo, useState } from "react";

import type { Channel } from "../channels/types";
import { FormField, SelectField, SwitchButton } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import type { Product } from "../../types";
import {
  listPortalSupportChannels,
  portalErrorMessage,
  replacePortalProducts,
  updateSupportPortal,
  type SupportPortal,
} from "./model";
import { PortalDomainSettings } from "./PortalDomainSettings";

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
  const [channels, setChannels] = useState<Channel[]>([]);
  const [selected, setSelected] = useState<Record<number, number | null>>({});
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    setName(portal.name);
    setSlug(portal.slug);
    setLocale(portal.defaultLocale);
    setSelected(Object.fromEntries(
      portal.products.map((item) => [item.productId, item.supportChannelId]),
    ));
  }, [portal]);

  useEffect(() => {
    listPortalSupportChannels(portal.id)
      .then((payload) => setChannels(payload.items))
      .catch(() => setChannels([]));
  }, [portal.id]);

  const supportChannels = useMemo(() => channels.filter((channel) => (
    channel.isActive
    && channel.department === "support"
    && channel.product
    && channel.policy.requiresAuthenticatedProductIdentity
    && !channel.policy.allowAnonymousSessions
  )), [channels]);

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

  async function saveProducts() {
    setBusy(true);
    setFeedback("");
    try {
      const items = Object.entries(selected).map(([productId, supportChannelId], index) => ({
        productId: Number(productId),
        supportChannelId,
        sortOrder: index,
      }));
      const payload = await replacePortalProducts(portal.id, items);
      onChanged(payload.portal);
      setFeedback("Продукты портала обновлены");
    } catch (caught) {
      setFeedback(portalErrorMessage(caught, "Не удалось сохранить продукты"));
    } finally {
      setBusy(false);
    }
  }

  function toggleProduct(productId: number) {
    setSelected((current) => {
      const next = { ...current };
      if (productId in next) delete next[productId];
      else next[productId] = null;
      return next;
    });
  }

  return (
    <div className="portal-settings-grid">
      <section className="portal-section">
        <div className="portal-section-heading">
          <div><h2>Основные настройки</h2><p>Название, публичный адрес и язык материалов.</p></div>
        </div>
        <div className="portal-settings-fields">
          <FormField disabled={!canManage} label="Название портала" value={name} onChange={canManage ? setName : undefined} wide />
          <FormField disabled={!canManage} label="Адрес CustoCRM" value={slug} onChange={canManage ? setSlug : undefined} mono wide />
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

      <section className="portal-section">
        <div className="portal-section-heading">
          <div><h2>Продукты и поддержка</h2><p>Выберите продукты и каналы, в которых клиенты смогут обратиться в поддержку.</p></div>
        </div>
        <div className="portal-product-list">
          {products.map((product) => {
            const enabled = product.id in selected;
            const options: Array<[string, string]> = [
              ["", "Без перехода в поддержку"],
              ...supportChannels
                .filter((channel) => channel.product?.id === product.id)
                .map((channel): [string, string] => [String(channel.id), channel.name]),
            ];
            return (
              <div className={enabled ? "is-enabled" : ""} key={product.id}>
                <SwitchButton
                  checked={enabled}
                  className="ui-switch"
                  disabled={!canManage}
                  label={`Добавить ${product.name}`}
                  onClick={() => toggleProduct(product.id)}
                />
                <span><strong>{product.name}</strong><small>{product.code}</small></span>
                {enabled && (
                  <SelectField
                    disabled={!canManage}
                    label="Канал поддержки"
                    value={String(selected[product.id] ?? "")}
                    onChange={(value) => setSelected((current) => ({
                      ...current,
                      [product.id]: value ? Number(value) : null,
                    }))}
                    options={options}
                  />
                )}
              </div>
            );
          })}
        </div>
        {canManage && <Button variant="secondary" disabled={busy} onClick={() => void saveProducts()}>Сохранить продукты</Button>}
      </section>
      <PortalDomainSettings portal={portal} canManage={canManage} onChanged={onChanged} />
      {feedback && <div className="portal-save-feedback">{feedback}</div>}
    </div>
  );
}
