"""Lossless field representation for heterogeneous scales and keyed counts."""

from copy import deepcopy

from chatballs.integrations.action_catalog.quality_values import encode


def support_payload(payload):
    payload = {**payload, "employees": [dict(employee) for employee in payload["employees"]]}
    for section in [payload, *payload["employees"]]:
        # The source shares quality detail rows between totals and employees.
        # Copy each feedback section independently to encode every scalar once.
        section["customerRatings"] = deepcopy(section["customerRatings"])
        section["qualityAnalysis"] = deepcopy(section["qualityAnalysis"])
        for group in section["customerRatings"]["groups"]:
            group["values"] = [{"value": int(value), "count": count}
                for value, count in group["values"].items()]
        quality = section["qualityAnalysis"]
        for group in quality["groups"]:
            group["scale"] = [encode(value) for value in group["scale"]]
            for name in ("originalValues", "effectiveValues"):
                for bucket in group[name]:
                    bucket["value"] = encode(bucket["value"])
        for row in quality["details"]:
            row["state"] = str(row["state"])
            for conclusion in row["conclusions"]:
                conclusion["scale"] = [encode(value) for value in conclusion["scale"]]
                for name in ("originalValue", "effectiveValue"):
                    conclusion[name] = encode(conclusion[name])
        for version in quality["versions"]:
            for criterion in version["criteria"]:
                criterion["scale"] = [encode(value) for value in criterion["scale"]]
                for name in ("originalSummary", "effectiveSummary"):
                    summary = criterion[name]
                    if "positiveValue" in summary:
                        summary["positiveValue"] = encode(summary["positiveValue"])
    return payload
