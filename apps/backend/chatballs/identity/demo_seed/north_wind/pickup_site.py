"""The local pickup catalogue uses the standard site-event invitation and scenario."""

from chatballs.identity.demo_seed import manifest
from chatballs.identity.demo_seed.north_wind.pickup_selection import (
    PICKUP_BUDGET_LIMIT,
    PICKUP_EVENT,
    PICKUP_TASK,
)
from chatballs.identity.demo_seed.north_wind.site_scenario import configure_site_scenario


def configure_pickup_site(refs):
    configure_site_scenario(refs, key="pickup", event=PICKUP_EVENT, task=PICKUP_TASK,
        copy=manifest.load("north_wind", refs.language)["pickupSite"], schema=[
            {"name": "category", "type": "string", "maxLength": 32, "required": True},
            {"name": "size", "type": "string", "maxLength": 2, "required": True},
            {"name": "city", "type": "string", "maxLength": 32, "required": True},
            {"name": "store", "type": "string", "maxLength": 8, "required": True},
            {"name": "budget", "type": "number", "minimum": 0, "maximum": PICKUP_BUDGET_LIMIT, "required": True},
        ])
