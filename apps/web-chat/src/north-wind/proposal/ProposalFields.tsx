import { Icon } from "../Icons";
import { t } from "../language";
import type { ProductId } from "../model";
import { money, sizes } from "../products";
import type { City, PartyResponse, ProposalDraft } from "./model";

type Props = {draft: ProposalDraft; onChange: (changes: Partial<ProposalDraft>) => void};

function NumberField({id, label, value, max, suffix, onChange}: {
  id: string; label: string; value: number; max?: number; suffix: string; onChange: (value: number) => void;
}) {
  return <div className="office-field">
    <label htmlFor={id}>{label}</label>
    <div className="office-number-wrap">
      <input id={id} type="number" inputMode="numeric" required min={0} max={max} step={1}
        value={value} onChange={event => onChange(Number(event.target.value))} />
      <span>{suffix}</span>
    </div>
  </div>;
}

export function PartyFields({draft, onChange, catalogue, problem}: Props & {catalogue: PartyResponse | null; problem: string}) {
  return <section className="quote-section" aria-labelledby="quote-selection-title">
    <div className="quote-section-heading"><span>1</span><h2 id="quote-selection-title">{t("proposal_selection")}</h2></div>
    <div className="quote-selection-fields">
      <div className="office-field quote-field-wide">
        <label htmlFor="quote-product">{t("proposal_model")}</label>
        <div className="office-select-wrap">
          <select id="quote-product" required value={draft.productId}
            onChange={event => onChange({productId: event.target.value as ProductId})}>
            <option value="" disabled>{t("proposal_choose_model")}</option>
            {catalogue?.options.map(option => <option key={option.id} value={option.id}>
              {t("proposal_option", {
                name: option.name, price: money(option.basePrice),
                stock: sizes.map(size => `${size} ${option.stock[size]}`).join(", "),
              })}
            </option>)}
          </select>
          <Icon name="ChevronDown" size={16} />
        </div>
      </div>
      {sizes.map(size => <NumberField key={size} id={`quote-quantity-${size}`}
        label={t("proposal_size_quantity", {size})} value={draft.quantities[size]} max={100}
        suffix={t("proposal_pieces")} onChange={value => onChange({quantities: {...draft.quantities, [size]: value}})} />)}
      <NumberField id="quote-budget" label={t("proposal_budget")} value={draft.budget}
        suffix={t("proposal_currency")} onChange={budget => onChange({budget})} />
      <div className="office-field quote-field-wide">
        <label htmlFor="quote-city">{t("proposal_city")}</label>
        <div className="office-select-wrap">
          <select id="quote-city" required value={draft.city} onChange={event => onChange({city: event.target.value as City})}>
            {catalogue?.destinations.map(city => <option key={city.id} value={city.id}>
              {t(`proposal_${city.id}`)} · {money(city.price)}
            </option>)}
          </select>
          <Icon name="ChevronDown" size={16} />
        </div>
      </div>
      <div className="office-field quote-field-wide">
        <label htmlFor="quote-address">{t("proposal_address")}</label>
        <input id="quote-address" required minLength={5} maxLength={240} autoComplete="street-address"
          placeholder={t("proposal_address_example")} value={draft.address} onChange={event => onChange({address: event.target.value})} />
      </div>
    </div>
    {problem && <div className="quote-stock-warning" role="status">
      <Icon name="AlertCircle" size={19} />
      <div>
        <strong>{t("proposal_check_batch")}</strong><p>{problem}</p>
        {catalogue && <div><span>{t("proposal_alternatives")}</span>
          {catalogue.options.filter(option => option.available && option.withinBudget).map(option =>
            <button type="button" key={option.id} onClick={() => onChange({productId: option.id})}>
              {option.name}<Icon name="ChevronRight" size={14} />
            </button>)}
        </div>}
      </div>
    </div>}
  </section>;
}

export function ContactFields({draft, onChange}: Props) {
  return <section className="quote-section" aria-labelledby="quote-contact-title">
    <div className="quote-section-heading"><span>2</span><h2 id="quote-contact-title">{t("proposal_contacts")}</h2></div>
    <div className="quote-contact-fields">
      <div className="office-field quote-field-wide">
        <label htmlFor="quote-company">{t("proposal_company")}</label>
        <input id="quote-company" required minLength={2} maxLength={120} autoComplete="organization"
          placeholder={t("proposal_company_example")} value={draft.company} onChange={event => onChange({company: event.target.value})} />
      </div>
      <div className="office-field">
        <label htmlFor="quote-name">{t("proposal_contact")}</label>
        <input id="quote-name" required minLength={2} maxLength={120} autoComplete="name"
          placeholder={t("proposal_contact_example")} value={draft.contact} onChange={event => onChange({contact: event.target.value})} />
      </div>
      <div className="office-field">
        <label htmlFor="quote-email">{t("proposal_email")}</label>
        <input id="quote-email" type="email" required maxLength={254} autoComplete="email"
          placeholder={t("proposal_email_example")} value={draft.email} onChange={event => onChange({email: event.target.value})} />
      </div>
    </div>
  </section>;
}
