"""Open the native widget on the verified sample customer's support thread."""

from chatballs.identity.demo_seed.north_wind.orders import find_order
from chatballs.identity.demo_seed.north_wind.prepared_widget import (
    issue_prepared_session,
    locked_dataset,
)
from chatballs.identity.demo_seed.north_wind.state import ShopError
from chatballs.tenancy.database import tenant_atomic


def issue_exchange_session(tenant, generation, *, customer, order_number):
    if customer != "andrey-after-purchase":
        raise ShopError("demo_dialog_unavailable")
    with tenant_atomic(tenant):
        dataset = locked_dataset(tenant, generation)
        find_order(dataset.shop_state, customer=customer, order_number=order_number)
        dialogs = dataset.shop_state.get("supportDialogs", {})
        binding = next(
            (dialog for dialog in dialogs.values() if dialog.get("orderNumber") == order_number),
            dialogs.get("exchange", {}) if order_number == 2042 else {},
        )
        return issue_prepared_session(dataset, binding)
