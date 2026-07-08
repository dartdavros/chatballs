from __future__ import annotations

from hub_platform.support.models import ProductSupportContract, SupportIdentitySnapshot


def support_contract_payload(contract: ProductSupportContract) -> dict[str, object]:
    return {
        "id": contract.id,
        "code": contract.code,
        "version": contract.version,
        "status": contract.status,
        "product": {"code": contract.product.code, "name": contract.product.name},
        "allowedChannels": [
            {"id": ch.id, "code": ch.code, "name": ch.name}
            for ch in contract.allowed_channels.all()
        ],
        "schemaJson": contract.schema_json,
        "identityMappingJson": contract.identity_mapping_json,
        "operatorUiJson": contract.operator_ui_json,
        "aiContextJson": contract.ai_context_json,
        "searchMappingJson": contract.search_mapping_json,
        "sensitiveFieldsJson": contract.sensitive_fields_json,
        "createdAt": contract.created_at.isoformat(),
        "updatedAt": contract.updated_at.isoformat(),
    }


def support_identity_snapshot_payload(snapshot: SupportIdentitySnapshot) -> dict[str, object]:
    # payload_json НЕ отдаётся — внутреннее; оператор получает operator_context_json.
    return {
        "id": snapshot.id,
        "product": {"code": snapshot.product.code, "name": snapshot.product.name},
        "contractCode": snapshot.contract_code,
        "subjectKey": snapshot.subject_key,
        "accountKey": snapshot.account_key,
        "displayName": snapshot.display_name,
        "displayEmail": snapshot.display_email,
        "operatorContextJson": snapshot.operator_context_json,
        "aiContextJson": snapshot.ai_context_json,
        "searchText": snapshot.search_text,
        "verifiedAt": snapshot.verified_at.isoformat(),
    }
