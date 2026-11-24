"""Download a fixed commercial proposal independently of local mail delivery."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.core import signing
from django.http import Http404, HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import override
from django.views import View

from chatballs.i18n import t
from chatballs.identity.demo_seed.north_wind.catalog import PRODUCTS
from chatballs.identity.demo_seed.north_wind.local_access import local_demo_enabled
from chatballs.identity.demo_seed.north_wind.state import ShopError, read_state
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.lookup import load_organization

_SALT = "north-wind-demo-proposal"
_POLICY = "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
_LABELS = (
    "brand", "trade", "heading", "company", "delivery", "contents", "model", "quantity", "unit",
    "subtotal", "catalogue", "discount", "total", "manager", "note",
)


def proposal_path(tenant, generation, number, *, history=False):
    token = signing.Signer(salt=_SALT).sign_object({
        "organization": tenant.organization_id, "generation": str(generation), "number": number,
        **({"history": True} if history else {}),
    })
    return reverse("demo-proposal-document", kwargs={"token": token})


class DemoProposalDocumentView(View):
    def get(self, request, token):
        if len(token) > 1024:
            raise Http404()
        try:
            binding = signing.Signer(salt=_SALT).unsign_object(token)
            organization = load_organization(binding["organization"])
            if organization is None:
                raise Http404()
            state = read_state(TenantContext.for_resource(organization), binding["generation"])
            if binding.get("history") is True:
                proposal = state["historyProposals"][binding["number"]]
            elif local_demo_enabled():
                proposal = state["proposals"][binding["number"]]
            else:
                raise Http404()
        except (signing.BadSignature, ShopError, KeyError) as error:
            raise Http404() from error
        language = state.get("historyLanguage", "ru")
        response = HttpResponse(render_proposal(proposal, language))
        response["Cache-Control"] = "private, no-store"
        response["Referrer-Policy"] = "no-referrer"
        response["Content-Security-Policy"] = _POLICY
        if request.GET.get("download") == "1":
            response["Content-Disposition"] = f'attachment; filename="{proposal["number"]}.html"'
        return response


def render_proposal(proposal, language):
    quote = proposal["quote"]
    until = datetime.fromisoformat(proposal["validUntil"]).astimezone(ZoneInfo("Europe/Moscow"))
    quantity = sum(quote["quantities"].values())
    catalogue = quote["unitPrice"] * quantity
    subtotal = quote["total"] - quote["delivery"]
    amounts = {"unit": subtotal // quantity, "subtotal": subtotal, "catalogue": catalogue,
               "discount": catalogue - subtotal, "delivery": quote["delivery"], "total": quote["total"]}

    def label(key, **values):
        return t(f"north_wind.proposal_{key}", language=language, **values)

    formatted = {key: f"RUB {value:,}" if language == "en" else f"{value:,}".replace(",", "\u202f") + "\u00a0₽"
                 for key, value in amounts.items()}
    with override(language):
        date = label("dated", created=date_format(until - timedelta(days=7), "j E Y"),
                     valid=date_format(until, "j E Y"))
    return render_to_string("north_wind/proposal.html", {
        "language": language, "policy": _POLICY, "proposal": proposal,
        "title": label("title", number=proposal["number"]), "labels": {key: label(key) for key in _LABELS},
        "date": date,
        "city": label(quote["city"]), "delivery_days": label("days_text", days=quote["days"]),
        "product": quote.get("productName") or PRODUCTS[quote["productId"]]["name"],
        "sizes": ", ".join(f"{size} × {count}" for size, count in quote["quantities"].items()),
        "quantity": quantity, "amounts": formatted, "discount": amounts["discount"] > 0,
    })
