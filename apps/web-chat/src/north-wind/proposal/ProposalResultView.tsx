import { useState } from "react";

import { Icon } from "../Icons";
import { fmt, t } from "../language";
import type { Product } from "../model";
import { money } from "../products";
import type { ProposalResult } from "./model";
import { ProposalViewer } from "./ProposalViewer";
import { QuoteBreakdown } from "./QuoteBreakdown";

export function ProposalResultView({result, products, onBack}: {
  result: ProposalResult; products: Product[]; onBack: () => void;
}) {
  const [documentOpen, showDocument] = useState(false);
  const {proposal} = result;
  const {quote} = proposal;
  const product = products.find(item => item.id === quote.productId);
  return <section className="quote-result">
    <button type="button" className="office-text-button quote-back" onClick={onBack}>
      <Icon name="ArrowLeft" size={15} />{t("proposal_back")}
    </button>
    <div className="quote-result-heading">
      <span><Icon name="FileText" size={27} /></span>
      <div><p>{t("proposal_heading")}</p><h1>{t("proposal_ready", {number: proposal.number})}</h1>
        <span>{proposal.company} · {proposal.contact}</span></div>
    </div>
    <div className="quote-result-layout">
      <div className="quote-result-document">
        <div className="quote-result-product">
          {product && <img src={product.photo} alt={product.name} />}
          <div><h2>{quote.productName}</h2>
            <p>{t("proposal_quantity_price", {quantity: quote.quantity, amount: money(quote.discountedUnit)})}</p>
            <span>{t("proposal_delivery_city", {city: t(`proposal_${quote.city}`)})}</span>
          </div>
        </div>
        <QuoteBreakdown quote={quote} />
        <div className="quote-result-address"><span>{t("proposal_address")}</span><p>{proposal.address}</p></div>
        <button type="button" className="office-primary-button" onClick={() => showDocument(true)}>
          <Icon name="FileText" size={17} />{t("proposal_open")}
        </button>
        <p className="quote-document-valid">{t("proposal_expires", {date: fmt.fullDate(proposal.validUntil)})}</p>
      </div>
      <aside className="quote-result-aside">
        <section className="quote-manager-card"><Icon name="User" size={22} />
          <div><h2>{t("proposal_lead", {number: proposal.crmReference})}</h2>
            <p>{t("proposal_owner")}</p><span>{t("proposal_lead_note")}</span></div>
        </section>
      </aside>
    </div>
    {documentOpen && <ProposalViewer proposal={proposal} onClose={() => showDocument(false)} />}
  </section>;
}
