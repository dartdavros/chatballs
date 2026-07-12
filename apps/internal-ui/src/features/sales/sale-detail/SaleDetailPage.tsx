import { Icon } from "../../../shared/icons";
import { EmptyState, LoadingState } from "../../../shared/ui";
import type { Role, RouteKey } from "../../../types";
import { StatusBadge } from "../orders/StatusBadge";
import { actorView, attributionLabel, dateTimeLong, money, sourceBadge, statusBadge } from "../registry/model";
import { SaleActionPanel } from "./SaleActionPanel";
import { SaleEventTimeline } from "./SaleEventTimeline";
import { useSaleDetail } from "./useSaleDetail";

const ENVIRONMENT_LABEL: Record<string, string> = { PRODUCTION: "Production", STAGING: "Staging", LOCAL: "Local" };

export function SaleDetailPage({
  saleId,
  role,
  setRoute,
  openDialog,
}: {
  saleId: number | null;
  role: Role;
  setRoute: (route: RouteKey) => void;
  openDialog: (conversationId: number) => void;
}) {
  const { sale, loading, error, busy, actionError, correct, partialRefund, refund, cancel } = useSaleDetail(saleId);

  if (loading) return <LoadingState />;
  if (error || !sale) return <EmptyState title="Не удалось загрузить продажу" />;

  const actor = actorView(sale.attributedActor);
  const items = sale.lineItems ?? [];

  return (
    <div className="order-detail-page">
      <button className="order-detail-back" type="button" onClick={() => setRoute("salesOrders")}><Icon name="arrow" size={15} />К продажам</button>

      <section className="ai-card order-detail-head">
        <div className="order-detail-title">
          <h1>{sale.externalSaleId || `Продажа #${sale.id}`}</h1>
          <StatusBadge value={statusBadge(sale.status)} />
          <StatusBadge value={sourceBadge(sale.sourceType)} />
        </div>
        <div className="order-detail-meta">
          <div><span>Клиент</span><b>{sale.contact ? sale.contact.name : "—"}</b></div>
          <div><span>Продукт</span><b>{sale.product ? sale.product.name : "—"}</b></div>
          <div><span>Внешний клиент</span><b>{sale.externalCustomerId || "—"}</b></div>
          <div><span>Окружение</span><b>{ENVIRONMENT_LABEL[sale.environment] ?? sale.environment}</b></div>
          <div><span>Дата продажи</span><b>{dateTimeLong(sale.occurredAt)}</b></div>
          <div><span>Последнее событие</span><b>{dateTimeLong(sale.lastEventAt)}</b></div>
          <div><span>Сумма</span><b>{money(sale.amountMinor, sale.currency)}</b></div>
          <div><span>Возврат</span><b>{sale.refundedAmountMinor > 0 ? money(sale.refundedAmountMinor, sale.currency) : "—"}</b></div>
          <div><span>Чистая выручка</span><b className="order-detail-amount">{money(sale.netAmountMinor, sale.currency)}</b></div>
        </div>
      </section>

      <section className="ai-card order-detail-head">
        <div className="order-detail-section-head"><h3>Атрибуция</h3></div>
        <div className="order-detail-meta">
          <div><span>Способ</span><b>{attributionLabel(sale.attributionMethod)}</b></div>
          <div><span>AI / сотрудник</span><b className={actor.ai ? "seller-ai" : undefined}>{actor.label}</b></div>
          <div>
            <span>Связанный диалог</span>
            {sale.conversationId ? (
              <b><button type="button" className="sale-link-button" onClick={() => openDialog(sale.conversationId as number)}>{`Диалог #${sale.conversationId}`}</button></b>
            ) : (
              <b>—</b>
            )}
          </div>
        </div>
      </section>

      <section className="ai-card ai-card--flush">
        <div className="order-detail-section-head"><h3>Коммерческий snapshot</h3></div>
        {items.length > 0 ? (
          <table className="sales-client-detail-table">
            <thead><tr><th>OFFER</th><th>НАЗВАНИЕ</th><th className="numeric">КОЛ-ВО</th><th className="numeric">СУММА</th></tr></thead>
            <tbody>
              {items.map((item, index) => (
                <tr key={index}>
                  <td><code>{String(item.offer_code ?? item.external_item_id ?? "—")}</code></td>
                  <td>{String(item.title ?? "—")}</td>
                  <td className="numeric">{String(item.quantity ?? 1)}</td>
                  <td className="numeric"><strong>{typeof item.amount_minor === "number" ? money(item.amount_minor, sale.currency) : "—"}</strong></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="sale-snapshot-empty">Позиции не переданы продуктом.</p>
        )}
      </section>

      <section className="ai-card order-detail-head">
        <div className="order-detail-section-head"><h3>История событий</h3></div>
        <SaleEventTimeline events={sale.events ?? []} />
      </section>

      {role === "OWNER" && (
        <SaleActionPanel busy={busy} actionError={actionError} onCorrect={correct} onPartialRefund={partialRefund} onRefund={refund} onCancel={cancel} />
      )}
    </div>
  );
}
