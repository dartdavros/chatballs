import { useEffect, useState } from "react";

import { api } from "../../../api/client";
import { EmptyState, LoadingState } from "../../../shared/ui";
import { StatusBadge } from "../orders/StatusBadge";
import { dateTime, money, sourceBadge, statusBadge, type ApiSale } from "../registry/model";

// Вкладка «Продажи» карточки клиента (SPEC-HUB-0014 §8.3): все продажи, разрешённые
// по диалогам и external identities этого контакта. Заменяет вкладку «Заказы».
export function SalesClientSalesTab({ contactId }: { contactId: number | null }) {
  const [sales, setSales] = useState<ApiSale[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (contactId === null) {
      setLoading(false);
      setError(true);
      return;
    }
    let active = true;
    api<{ items: ApiSale[] }>(`/api/v1/sales/?contact=${contactId}`)
      .then((data) => active && setSales(data.items))
      .catch(() => active && setError(true))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [contactId]);

  if (loading) return <LoadingState variant="inline" />;
  if (error) return <EmptyState title="Не удалось загрузить продажи" />;
  if (sales.length === 0) return <EmptyState title="У контакта ещё нет продаж" />;

  return (
    <div className="sales-client-table-card">
      <table className="sales-client-detail-table">
        <thead>
          <tr>
            <th>ПРОДАЖА</th>
            <th>ДАТА</th>
            <th>ПРОДУКТ</th>
            <th className="numeric">СУММА</th>
            <th className="numeric">ЧИСТАЯ</th>
            <th>СОСТОЯНИЕ</th>
            <th>ИСТОЧНИК</th>
          </tr>
        </thead>
        <tbody>
          {sales.map((sale) => (
            <tr key={sale.id}>
              <td><code>{sale.externalSaleId || `#${sale.id}`}</code></td>
              <td>{dateTime(sale.occurredAt)}</td>
              <td>{sale.product ? sale.product.name : "—"}</td>
              <td className="numeric"><strong>{money(sale.amountMinor, sale.currency)}</strong></td>
              <td className="numeric"><strong>{money(sale.netAmountMinor, sale.currency)}</strong></td>
              <td><StatusBadge value={statusBadge(sale.status)} /></td>
              <td><StatusBadge value={sourceBadge(sale.sourceType)} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
