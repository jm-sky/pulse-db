"""Abstract storage adapter for file operations."""

from abc import ABC, abstractmethod


class StorageAdapter(ABC):
    """Abstract storage adapter for file operations."""

    @abstractmethod
    async def upload(
        self,
        file_content: bytes,
        destination_path: str,
        content_type: str,
        metadata: dict | None = None,
    ) -> str:
        """
        Upload file to storage.

        Args:
            file_content: File content as bytes
            destination_path: Destination path/key for the file
            content_type: MIME type of the file
            metadata: Optional metadata dictionary

        Returns:
            Full path/key to stored file
        """
        pass

    @abstractmethod
    async def download(self, file_path: str) -> bytes:
        """
        Download file from storage.

        Args:
            file_path: Path/key of file to download

        Returns:
            File content as bytes
        """
        pass

    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """
        Delete file from storage.

        Args:
            file_path: Path/key of file to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        pass

    @abstractmethod
    async def exists(self, file_path: str) -> bool:
        """
        Check if file exists in storage.

        Args:
            file_path: Path/key of file to check

        Returns:
            True if file exists, False otherwise
        """
        pass

    @abstractmethod
    async def get_url(self, file_path: str, expires_in: int = 3600) -> str:
        """
        Get accessible URL for file.

        Args:
            file_path: Path/key of file
            expires_in: URL expiration time in seconds (for signed URLs)

        Returns:
            Accessible URL for the file
        """
        pass

    @abstractmethod
    async def get_available_space(self) -> int | None:
        """
        Get available storage space in bytes.

        Returns:
            Available space in bytes, or None if unlimited/unknown
        """
        pass
