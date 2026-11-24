"""Read only a trusted pickup task and its already validated client data."""

import json

from chatballs.identity.demo_seed.north_wind.pickup_selection import (
    PICKUP_TASK,
    catalogue_selection,
)

_TASK = "Trusted scenario task for the first reply:\n" + PICKUP_TASK
_DATA = "Site event data: "


def pickup_context(messages):
    task = next((index for index, message in enumerate(messages)
                 if message.role == "system" and message.content == _TASK), None)
    if task is None:
        return None
    for message in messages[:task]:
        if message.role != "system":
            continue
        for line in message.content.splitlines():
            if line.startswith(_DATA):
                try:
                    values = json.loads(json.loads('"' + line[len(_DATA):] + '"'))
                except (TypeError, ValueError):
                    return None
                arguments = catalogue_selection(values)
                if arguments is None:
                    return None
                return task, arguments
    return None
