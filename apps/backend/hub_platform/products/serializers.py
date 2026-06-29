from hub_platform.products.models import Offer, Price, Product


def price_payload(price: Price) -> dict[str, object]:
    return {
        "id": price.id,
        "version": price.version,
        "amountMinor": price.amount_minor,
        "currency": price.currency,
        "billingPeriod": price.billing_period,
        "validFrom": price.valid_from.isoformat(),
        "validUntil": price.valid_until.isoformat() if price.valid_until else None,
        "isActive": price.is_active,
    }


def offer_payload(offer: Offer) -> dict[str, object]:
    return {
        "id": offer.id,
        "code": offer.code,
        "name": offer.name,
        "description": offer.description,
        "fulfillmentType": offer.fulfillment_type,
        "paymentType": offer.payment_type,
        "primaryBoxOfferId": offer.primary_box_offer_id,
        "isActive": offer.is_active,
        "aiOfferable": offer.ai_offerable,
        "fiscalName": offer.fiscal_name,
        "accessSchema": offer.access_schema,
        "prices": [price_payload(price) for price in offer.prices.all()],
    }


def product_payload(product: Product) -> dict[str, object]:
    return {
        "id": product.id,
        "code": product.code,
        "name": product.name,
        "status": product.status,
        "siteUrl": product.site_url,
        "summary": product.summary,
        "salesDescription": product.sales_description,
        "departments": [
            {"id": link.department_id, "code": link.department.code, "name": link.department.name}
            for link in product.department_links.all()
        ],
        "offers": [offer_payload(offer) for offer in product.offers.all()],
        "createdAt": product.created_at.isoformat(),
        "updatedAt": product.updated_at.isoformat(),
    }
