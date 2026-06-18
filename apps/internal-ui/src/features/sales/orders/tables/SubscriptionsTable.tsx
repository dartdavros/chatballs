import { Icon } from "../../../../shared/icons";
import { MonoLink, StatusBadge } from "../StatusBadge";
import type { SalesSubscription } from "../types";

export function SubscriptionsTable({ rows }: { rows: SalesSubscription[] }) {
  if (rows.length === 0) return null;
  return (
    <table className="sales-orders-table subscriptions">
      <thead>
        <tr>
          <th>ПОДПИСКА</th><th>КЛИЕНТ</th><th>OFFER</th><th>СТАТУС</th><th>ПЕРИОД</th><th>СЛЕД. СПИСАНИЕ</th><th>ENTITLEMENT</th><th />
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id}>
            <td><MonoLink>{row.id}</MonoLink></td>
            <td className="strong-text">{row.client}</td>
            <td>{row.offer}</td>
            <td><StatusBadge value={row.status} /></td>
            <td className="nowrap">{row.period}</td>
            <td className="nowrap">{row.next}</td>
            <td>{row.entitlement}</td>
            <td className="row-actions"><button type="button" aria-label="Действия подписки"><Icon name="more" size={17} /></button></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
