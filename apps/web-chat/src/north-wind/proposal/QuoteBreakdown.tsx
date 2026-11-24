import { t, tn } from "../language";
import { money } from "../products";
import type { PartyQuote } from "./model";

export function QuoteBreakdown({quote}: {quote: PartyQuote}) {
  const beforeDiscount = quote.unitPrice * quote.quantity;
  return <div className="quote-breakdown">
    <div><span>{quote.quantity} × {money(quote.unitPrice)}</span><strong>{money(beforeDiscount)}</strong></div>
    {quote.discountPercent > 0 && <div className="quote-discount">
      <span>{t("proposal_batch_discount", {percent: quote.discountPercent})}</span>
      <strong>−{money(beforeDiscount - quote.subtotal)}</strong>
    </div>}
    <div className="quote-subtotal">
      <span>{t(quote.discountPercent > 0 ? "proposal_sets_discounted" : "proposal_sets")}
        <small>{t("proposal_unit_amount", {price: money(quote.discountedUnit)})}</small>
      </span>
      <strong>{money(quote.subtotal)}</strong>
    </div>
    <div><span>{t("proposal_delivery", {city: t(`proposal_${quote.city}`)})}
      <small>{tn("proposal_days", quote.days)}</small></span><strong>{money(quote.delivery)}</strong></div>
    <div className="quote-total"><span>{t("total")}</span><strong>{money(quote.total)}</strong></div>
  </div>;
}
