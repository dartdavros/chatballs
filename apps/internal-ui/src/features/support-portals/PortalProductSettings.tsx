import { useEffect, useMemo, useState } from "react";

import { SelectField, SwitchButton } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import type { Product } from "../../types";
import {
  portalErrorMessage,
  replacePortalProducts,
  type PortalWidgetOption,
  type SupportPortal,
} from "./model";

export function PortalProductSettings({
  portal,
  products,
  widgets,
  canManage,
  onChanged,
}: {
  portal: SupportPortal;
  products: Product[];
  widgets: PortalWidgetOption[];
  canManage: boolean;
  onChanged: (portal: SupportPortal) => void;
}) {
  const [selected, setSelected] = useState<Record<number, number | null>>({});
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    setSelected(Object.fromEntries(
      portal.products.map((item) => [item.productId, item.supportWidgetId]),
    ));
  }, [portal.products]);

  const supportWidgets = useMemo(
    () => widgets.filter((widget) => widget.mode === "AUTHENTICATED_PRODUCT"),
    [widgets],
  );

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
      const items = Object.entries(selected).map(([productId, supportWidgetId], index) => ({
        productId: Number(productId),
        supportWidgetId,
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
        <div><h2>Продукты и поддержка</h2><p>Выберите продукты и виджеты, через которые клиенты смогут обратиться в поддержку.</p></div>
      </div>
      <div className="portal-product-list">
        {products.map((product) => {
          const enabled = product.id in selected;
          const options: Array<[string, string]> = [
            ["", "Без перехода в поддержку"],
            ...supportWidgets
              .filter((widget) => widget.channel?.productId === product.id)
              .map((widget): [string, string] => [String(widget.id), widget.name]),
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
                  label="Виджет поддержки"
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
