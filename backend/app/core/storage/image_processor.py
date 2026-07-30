"""Image processing utilities with async support."""

import asyncio
import io

from PIL import Image
from PIL.Image import Image as PILImage

from app.core.storage.exceptions import CorruptedImageError


class ImageProcessor:
    """Image processing utilities."""

    def __init__(
        self,
        max_width: int = 1920,
        max_height: int = 1920,
        jpeg_quality: int = 85,
        convert_to_webp: bool = False,
    ):
        """
        Initialize image processor.

        Args:
            max_width: Maximum image width in pixels
            max_height: Maximum image height in pixels
            jpeg_quality: JPEG compression quality (1-100)
            convert_to_webp: Convert all images to WebP format
        """
        self.max_width = max_width
        self.max_height = max_height
        self.jpeg_quality = jpeg_quality
        self.convert_to_webp = convert_to_webp

    async def process_image(self, image_bytes: bytes, mime_type: str) -> tuple[bytes, str, int, int]:
        """
        Process image: resize, compress, optionally convert to WebP.

        Args:
            image_bytes: Image file content as bytes
            mime_type: Original MIME type

        Returns:
            Tuple of (processed_bytes, new_mime_type, width, height)
        """
        # Run synchronous PIL operations in thread pool to avoid blocking
        return await asyncio.to_thread(self._process_image_sync, image_bytes, mime_type)

    def _process_image_sync(self, image_bytes: bytes, mime_type: str) -> tuple[bytes, str, int, int]:
        """
        Synchronous image processing implementation.

        This runs in a thread pool to avoid blocking the event loop.

        Raises:
            CorruptedImageError: If image is corrupted or truncated
        """
        try:
            # Open image
            img: PILImage = Image.open(io.BytesIO(image_bytes))
            # Load image to detect truncation early
            img.load()
        except OSError as e:
            # Handle truncated/corrupted image files
            error_msg = str(e).lower()
            if "truncated" in error_msg or "cannot identify" in error_msg:
                raise CorruptedImageError("Image file is corrupted or truncated") from e
            raise CorruptedImageError(f"Failed to process image: {e}") from e
        except Exception as e:
            # Catch other PIL errors (invalid format, etc.)
            raise CorruptedImageError(f"Failed to process image: {e}") from e

        # Convert RGBA to RGB if saving as JPEG
        if img.mode == "RGBA" and not self.convert_to_webp:
            # Create white background for transparency
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
            img = background

        # Get original dimensions
        original_width, original_height = img.size

        # Resize if needed (preserve aspect ratio)
        try:
            if original_width > self.max_width or original_height > self.max_height:
                img.thumbnail((self.max_width, self.max_height), Image.Resampling.LANCZOS)
        except OSError as e:
            # Handle errors during thumbnail operation (e.g., truncated image)
            error_msg = str(e).lower()
            if "truncated" in error_msg:
                raise CorruptedImageError("Image file is corrupted or truncated") from e
            raise CorruptedImageError(f"Failed to resize image: {e}") from e

        width, height = img.size

        # Save processed image
        output = io.BytesIO()

        try:
            if self.convert_to_webp:
                img.save(output, format="WEBP", quality=self.jpeg_quality, method=6)
                mime_type = "image/webp"
            elif mime_type in ["image/jpeg", "image/jpg"]:
                img.save(output, format="JPEG", quality=self.jpeg_quality, optimize=True)
            elif mime_type == "image/png":
                img.save(output, format="PNG", optimize=True)
            elif mime_type == "image/gif":
                img.save(output, format="GIF", optimize=True)
            else:
                # Keep original format
                img_format = img.format or "JPEG"
                img.save(output, format=img_format, quality=self.jpeg_quality, optimize=True)
        except OSError as e:
            # Handle errors during save (e.g., corrupted image data)
            error_msg = str(e).lower()
            if "truncated" in error_msg:
                raise CorruptedImageError("Image file is corrupted or truncated") from e
            raise CorruptedImageError(f"Failed to save processed image: {e}") from e

        output.seek(0)
        processed_bytes = output.read()

        return processed_bytes, mime_type, width, height

    async def validate_image(self, image_bytes: bytes) -> bool:
        """
        Validate that bytes represent a valid image.

        Args:
            image_bytes: Image file content as bytes

        Returns:
            True if valid image, False otherwise
        """
        return await asyncio.to_thread(self._validate_image_sync, image_bytes)

    def _validate_image_sync(self, image_bytes: bytes) -> bool:
        """Synchronous image validation."""
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()
            return True
        except Exception:
            return False
