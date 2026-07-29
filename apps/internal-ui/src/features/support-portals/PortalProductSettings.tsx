import { useEffect, useMemo, useState } from "react";

import type { Channel } from "../channels/types";
import { SelectField, SwitchButton } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import type { Product } from "../../types";
import {
  portalErrorMessage,
  replacePortalProducts,
  type SupportPortal,
} from "./model";

export function PortalProductSettings({
  portal,
  products,
  channels,
  canManage,
  onChanged,
}: {
  portal: SupportPortal;
  products: Product[];
  channels: Channel[];
  canManage: boolean;
  onChanged: (portal: SupportPortal) => void;
}) {
  const [selected, setSelected] = useState<Record<number, number | null>>({});
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    setSelected(Object.fromEntries(
      portal.products.map((item) => [item.productId, item.supportChannelId]),
    ));
  }, [portal.products]);

  const supportChannels = useMemo(() => channels.filter((channel) => (
    channel.isActive
    && channel.department === "support"
    && channel.product
    && channel.policy.requiresAuthenticatedProductIdentity
    && !channel.policy.allowAnonymousSessions
  )), [channels]);

  function toggleProduct(productId: number) {
    setSelected((current) => {
      const next = { ...current };
      if (productId in next) delete next[productId];
      else next[productId] = null;
      return next;
    });
  }

  async function save() {
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

  return (
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
      {canManage && <Button variant="secondary" disabled={busy} onClick={() => void save()}>Сохранить продукты</Button>}
      {feedback && <div className="portal-save-feedback">{feedback}</div>}
    </section>
  );
}
