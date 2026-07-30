"""Storage module for file uploads."""

from app.core.storage.adapter import StorageAdapter
from app.core.storage.exceptions import (
    CorruptedImageError,
    ImageProcessingError,
    InvalidImageFormatError,
)
from app.core.storage.factory import get_storage_adapter
from app.core.storage.image_processor import ImageProcessor
from app.core.storage.local_adapter import LocalStorageAdapter

__all__ = [
    "StorageAdapter",
    "LocalStorageAdapter",
    "ImageProcessor",
    "get_storage_adapter",
    "ImageProcessingError",
    "CorruptedImageError",
    "InvalidImageFormatError",
]
