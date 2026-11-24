import { Icon } from "../Icons";
import { t } from "../language";
import type { Product } from "../model";
import type { ShopMessageKey } from "../messages.ru";
import { PartyFields, ContactFields } from "./ProposalFields";
import { ProposalResultView } from "./ProposalResultView";
import { QuoteBreakdown } from "./QuoteBreakdown";
import { useProposal } from "./useProposal";
import "./office-fields.css";
import "./quote.css";

const errorCopy: Partial<Record<string, ShopMessageKey>> = {
  party_stock_unavailable: "proposal_stock_error", party_budget_exceeded: "proposal_budget_error",
  invalid_party: "proposal_draft_error", quote_changed: "proposal_quote_changed",
  unknown_demo_address: "proposal_email_error",
};

export function ProposalForm({token, products, onBack}: {token: string; products: Product[]; onBack: () => void}) {
  const form = useProposal(token);
  const {draft, catalogue, quote, result, pending, error} = form;
  if (result) return <div className="north-wind-proposal"><ProposalResultView result={result} products={products} onBack={onBack} /></div>;

  const selected = catalogue?.options.find(option => option.id === draft.productId);
  const product = products.find(item => item.id === draft.productId);
  const recipients = catalogue?.emailRecipients ?? [];
  const emailValid = recipients.includes(draft.email.trim().toLowerCase());
  let problem = "";
  if (selected && !selected.available) problem = t("proposal_stock_error");
  else if (selected && !selected.withinBudget) problem = t("proposal_budget_error");

  return <div className="north-wind-proposal">
    <form className="quote-form" onSubmit={event => { event.preventDefault(); void form.submit(); }}>
      <div className="quote-heading">
        <button type="button" className="office-text-button quote-back" onClick={onBack}>
          <Icon name="ArrowLeft" size={15} />{t("proposal_back")}
        </button>
        <h1>{t("proposal_title")}</h1><p>{t("proposal_intro")}</p>
      </div>
      <div className="quote-layout">
        <div className="quote-form-main">
          <PartyFields draft={draft} catalogue={catalogue} problem={problem} onChange={form.update} />
          <ContactFields draft={draft} recipients={recipients} onChange={form.update} />
        </div>
        <aside className="quote-review" aria-labelledby="quote-review-title">
          <div className="quote-section-heading"><span>3</span><h2 id="quote-review-title">{t("proposal_review")}</h2></div>
          {product && <div className="quote-review-product">
            <img src={product.photo} alt={product.name} /><div><h3>{product.name}</h3><p>{product.material}</p>
              <span>{Object.values(draft.quantities).reduce((sum, count) => sum + count, 0)} {t("proposal_pieces")}</span></div>
          </div>}
          {quote ? <><QuoteBreakdown quote={quote} /><p className="quote-stock-confirmation">
            <Icon name="CheckCircle2" size={15} />{t("proposal_batch_available", {count: quote.quantity})}
          </p></> : <div className="quote-review-empty">
            <Icon name={problem ? "AlertCircle" : "FileText"} size={24} />
            <p>{problem || t(draft.productId ? "proposal_calculating" : "proposal_select_to_quote")}</p>
          </div>}
          <label className="quote-email-confirmation">
            <input type="checkbox" required checked={draft.confirmed} disabled={!emailValid}
              onChange={event => form.update({confirmed: event.target.checked})} />
            <span>{t("proposal_confirm_prefix")} <strong>{draft.email || t("proposal_confirm_email")}</strong>
              {" "}{t("proposal_confirm_suffix")}</span>
          </label>
          {draft.email && !emailValid && <p className="office-field-error quote-confirm-error">{t("proposal_email_error")}</p>}
          {error && <p className="quote-submit-error" role="alert">{t(errorCopy[error] ?? "proposal_server_error")}</p>}
          <button type="submit" className="office-primary-button" disabled={pending || !quote || !emailValid}>
            {t(pending ? "proposal_submitting" : "proposal_submit")}
            <Icon name={pending ? "LoaderCircle" : "ArrowRight"} size={17} />
          </button>
          <p className="quote-review-note">{t("proposal_review_note")}</p>
        </aside>
      </div>
    </form>
  </div>;
}
