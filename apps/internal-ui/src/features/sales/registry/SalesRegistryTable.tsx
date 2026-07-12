import { Icon } from "../../../shared/icons";
import { MonoLink, StatusBadge } from "../orders/StatusBadge";
import type { SaleRow } from "./model";

export function SalesRegistryTable({ rows, openSale, openDialog }: { rows: SaleRow[]; openSale: (id: number) => void; openDialog: (conversationId: number) => void }) {
  if (rows.length === 0) return null;
  return (
    <table className="sales-orders-table registry">
      <thead>
        <tr>
          <th>ПРОДАЖА</th>
          <th>ДАТА</th>
          <th>КЛИЕНТ</th>
          <th>ПРОДУКТ</th>
          <th className="numeric">СУММА</th>
          <th className="numeric">ВОЗВРАТ</th>
          <th className="numeric">ЧИСТАЯ</th>
          <th>СОСТОЯНИЕ</th>
          <th>ИСТОЧНИК</th>
          <th>АТРИБУЦИЯ</th>
          <th>AI / СОТРУДНИК</th>
          <th>ДИАЛОГ</th>
          <th>СИНХРОНИЗАЦИЯ</th>
          <th />
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.saleId}>
            <td><MonoLink onClick={() => openSale(row.saleId)}>{row.external}</MonoLink></td>
            <td className="nowrap">{row.date}</td>
            <td className="strong-text">{row.client}</td>
            <td>{row.product}</td>
            <td className="numeric nowrap"><strong>{row.amount}</strong></td>
            <td className="numeric nowrap">{row.refund}</td>
            <td className="numeric nowrap"><strong>{row.net}</strong></td>
            <td><StatusBadge value={row.status} /></td>
            <td><StatusBadge value={row.source} /></td>
            <td className="muted-cell">{row.attribution}</td>
            <td><span className={row.actor.ai ? "seller-ai" : "seller"}>{row.actor.label}</span></td>
            <td>
              {row.conversationId ? (
                <MonoLink onClick={() => openDialog(row.conversationId as number)}>{`#${row.conversationId}`}</MonoLink>
              ) : (
                <span className="muted-dash">—</span>
              )}
            </td>
            <td className="nowrap muted-cell">{row.synced}</td>
            <td className="row-actions">
              <button type="button" aria-label="Открыть карточку продажи" onClick={() => openSale(row.saleId)}><Icon name="more" size={17} /></button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
