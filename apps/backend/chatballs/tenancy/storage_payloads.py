"""Public storage state: preserve the ordinary redacted settings contract."""
from chatballs.tenancy import storage_settings as ss


def _mask(value: str) -> str:
    if not value:
        return ""
    return f"{value[:4]}…{value[-2:]}" if len(value) > 8 else "•" * len(value)


def storage_payload(row: ss.StorageSettings) -> dict[str, object]:
    return {
        "backend": row.backend,
        "s3Bucket": row.s3_bucket,
        "s3EndpointUrl": row.s3_endpoint_url,
        "s3Region": row.s3_region,
        "s3AccessKeyMasked": _mask(row.s3_access_key),
        "s3HasSecretKey": bool(row.s3_secret_key),
        "s3AddressingStyle": row.s3_addressing_style or "path",
        "s3Configured": row.s3_configured,
        "s3VerifiedAt": row.s3_verified_at.isoformat() if row.s3_verified_at else None,
        "s3LastError": row.s3_last_error,
        "migration": {
            "status": row.migration_status,
            "total": row.migration_total,
            "done": row.migration_done,
            "error": row.migration_error,
            "startedAt": row.migration_started_at.isoformat() if row.migration_started_at else None,
            "finishedAt": row.migration_finished_at.isoformat() if row.migration_finished_at else None,
        },
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }
