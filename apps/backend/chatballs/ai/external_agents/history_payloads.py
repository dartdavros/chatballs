"""Shared signed cursor and exact history page envelope for the JSON budget."""

from django.core import signing

CURSOR_SALT = "external-agent-text-history-v1"


def cursor(row, offset=None):
    return signing.Signer(salt=CURSOR_SALT).sign_object([str(row.public_id), str(row.authorization_id), offset])


def page(row, items, start):
    return {"version": "1", "items": items, "snapshotCursor": cursor(row),
            "nextCursor": cursor(row, start) if start else None, "hasMore": bool(start),
            "dataPolicyRevision": row.authorization_versions["policy"]}
