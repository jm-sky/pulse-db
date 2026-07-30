"""Custom exceptions for storage and image processing."""


class ImageProcessingError(Exception):
    """Base exception for image processing errors."""

    pass


class CorruptedImageError(ImageProcessingError):
    """Raised when image file is corrupted or truncated."""

    pass


class InvalidImageFormatError(ImageProcessingError):
    """Raised when image format is invalid or unsupported."""

    pass
