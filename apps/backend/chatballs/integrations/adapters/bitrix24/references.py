"""crm.*.list search, per the official Bitrix24 REST list/filter contract."""

from urllib.parse import urlsplit

from chatballs.integrations.adapters.references import EntityReferences, ReferenceCandidate


def references(entity):
    # https://apidocs.bitrix24.ru/api-reference/crm/contacts/crm-contact-list.html
    # Search only presents candidates; the caller must select one explicitly.
    field = "NAME" if entity == "contact" else "TITLE"
    def arguments(query):
        return {"filter": {"ID" if query.isdecimal() else f"%{field}": query},
                "select": ["ID", field], "order": {"ID": "ASC"}, "start": 0}
    def candidates(value):
        return tuple(ReferenceCandidate(str(row["ID"]), str(row.get(field) or row["ID"]))
            for row in value if isinstance(row, dict) and row.get("ID"))
    def record_url(credentials, identity):
        portal = urlsplit(credentials.get("url", ""))
        if portal.scheme != "https" or not portal.hostname or not identity.isdecimal():
            return ""
        # Retain only the portal origin, never the webhook's secret path.
        return f"https://{portal.netloc}/crm/{entity}/details/{identity}/"
    return EntityReferences(f"{entity}.list", arguments, candidates, record_url)
