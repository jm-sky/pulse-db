"""Storage adapter factory."""

from app.core.config import settings
from app.core.storage.adapter import StorageAdapter
from app.core.storage.local_adapter import LocalStorageAdapter


def get_storage_adapter() -> StorageAdapter:
    """
    Get storage adapter based on configuration.

    Returns:
        Configured storage adapter instance

    Raises:
        ValueError: If storage type is unsupported
    """
    storage_type = settings.storage.type

    if storage_type == "local":
        return LocalStorageAdapter(
            base_path=settings.storage.local_path,
            base_url=settings.storage.base_url,
        )
    elif storage_type == "s3":
        # Lazy import to avoid requiring S3 dependencies for local storage
        from app.core.storage.s3_adapter import S3StorageAdapter

        return S3StorageAdapter(
            bucket_name=settings.storage.s3_bucket,
            aws_access_key_id=settings.storage.s3_access_key,
            aws_secret_access_key=settings.storage.s3_secret_key,
            region_name=settings.storage.s3_region,
            endpoint_url=settings.storage.s3_endpoint_url,
            public_endpoint_url=settings.storage.s3_public_endpoint_url,
        )
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")
