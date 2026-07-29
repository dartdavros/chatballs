import { formatDate } from "../../shared/utils";
import {
  formatMoney,
  formatQuotaValue,
  subscriptionStatusLabel,
  type SubscriptionSummary,
} from "./model";

export function CloudSubscriptionPanel({
  subscription,
}: {
  subscription: SubscriptionSummary;
}) {
  const period = subscription.periodStart && subscription.periodEnd
    ? `${formatDate(subscription.periodStart)} — ${formatDate(subscription.periodEnd)}`
    : "—";

  return (
    <section className="administration-card administration-subscription">
      <div className="administration-subscription-summary">
        <div>
          <span>Тариф</span>
          <strong>{subscription.planName}</strong>
        </div>
        <div>
          <span>Статус</span>
          <strong>{subscriptionStatusLabel(subscription.status)}</strong>
        </div>
        <div>
          <span>AI-агенты</span>
          <strong>{subscription.aiAgentQuantity.toLocaleString("ru-RU")}</strong>
        </div>
        <div>
          <span>Стоимость в месяц</span>
          <strong>{formatMoney(subscription.monthlyChargeMinor, subscription.currency)}</strong>
        </div>
        <div className="is-wide">
          <span>Текущий период</span>
          <strong>{period}</strong>
        </div>
      </div>
      {subscription.quotas.length > 0 && (
        <div className="administration-quotas">
          <h3>Использование</h3>
          <div>
            {subscription.quotas.map((quota) => (
              <article key={quota.key}>
                <span>{quota.label}</span>
                <strong>
                  {formatQuotaValue(quota.used, quota.unit)}
                  {quota.limit === null
                    ? ""
                    : ` из ${formatQuotaValue(quota.limit, quota.unit)}`}
                </strong>
              </article>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
