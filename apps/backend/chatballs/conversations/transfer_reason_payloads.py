"""Shared transfer reason contract."""



def reason_option_payload(reason):
    return {
        "id": reason.pk, "code": reason.code, "name": reason.name,
        "isActive": reason.is_active,
    }

def reason_payload(reason):
    return {
        **reason_option_payload(reason),
        "usageCount": getattr(reason, "usage_count", 0),
        "previousName": reason.previous_name,
        "renamedAt": reason.renamed_at.isoformat() if reason.renamed_at else None,
    }
