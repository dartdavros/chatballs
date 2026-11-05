"""Validate arbitrary JSON data without interpreting references or file grants."""

import math


def valid_json(value, depth=0):
    if depth > 64:
        return False
    if value is None or type(value) in (str, bool, int):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is list:
        return all(valid_json(child, depth + 1) for child in value)
    if type(value) is dict:
        return all(type(key) is str and valid_json(child, depth + 1) for key, child in value.items())
    return False
