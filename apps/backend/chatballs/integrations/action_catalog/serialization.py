"""Native payloads use the same primitive JSON representation as product APIs."""

import json

from rest_framework.utils.encoders import JSONEncoder


def json_data(value):
    return json.loads(json.dumps(value, cls=JSONEncoder, ensure_ascii=False))
