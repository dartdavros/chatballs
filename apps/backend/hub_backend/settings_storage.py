import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


def build_storage_settings(
    *,
    base_dir: Path,
    debug: bool,
    testing: bool,
) -> tuple[str, Path, dict[str, dict]]:
    backend = os.environ.get(
        "CUS_STORAGE_BACKEND",
        "filesystem" if debug or testing else "s3",
    ).lower()
    if backend not in {"filesystem", "s3"}:
        raise ImproperlyConfigured("CUS_STORAGE_BACKEND must be 's3' or 'filesystem'")
    if not debug and not testing and backend != "s3":
        raise ImproperlyConfigured("Production tenant storage must use the S3 backend")

    default_storage: dict = {
        "BACKEND": "hub_platform.tenancy.storage_backends.TenantFileSystemStorage",
    }
    if backend == "s3":
        bucket_name = os.environ.get("CUS_S3_BUCKET", "")
        if not bucket_name:
            raise ImproperlyConfigured("CUS_S3_BUCKET is required for S3 storage")
        default_storage = {
            "BACKEND": "hub_platform.tenancy.storage_backends.TenantS3Storage",
            "OPTIONS": {
                "bucket_name": bucket_name,
                "endpoint_url": os.environ.get("CUS_S3_ENDPOINT_URL") or None,
                "region_name": os.environ.get("CUS_S3_REGION") or None,
                "access_key": os.environ.get("CUS_S3_ACCESS_KEY") or None,
                "secret_key": os.environ.get("CUS_S3_SECRET_KEY") or None,
                "addressing_style": os.environ.get("CUS_S3_ADDRESSING_STYLE", "path"),
                "default_acl": None,
                "file_overwrite": False,
                "querystring_auth": True,
                "querystring_expire": int(
                    os.environ.get("CUS_S3_URL_EXPIRY_SECONDS", "900")
                ),
            },
        }

    media_root = Path(os.environ.get("CUS_MEDIA_ROOT", base_dir / "media"))
    storages = {
        "default": default_storage,
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
            if testing
            else "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    return backend, media_root, storages
