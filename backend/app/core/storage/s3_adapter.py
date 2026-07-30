"""AWS S3 storage adapter."""

try:
    import aioboto3
    from botocore.exceptions import ClientError

    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False

from app.core.storage.adapter import StorageAdapter


class S3StorageAdapter(StorageAdapter):
    """AWS S3 storage adapter."""

    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region_name: str = "us-east-1",
        endpoint_url: str | None = None,
        public_endpoint_url: str | None = None,
    ):
        """
        Initialize S3 storage adapter.

        Args:
            bucket_name: S3 bucket name
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            region_name: AWS region name
            endpoint_url: Custom endpoint URL (for S3-compatible services like MinIO, DigitalOcean Spaces)
            public_endpoint_url: Public endpoint URL for generating accessible URLs (e.g., http://localhost:9000 for MinIO in Docker).
                If not set, uses endpoint_url.
        """
        if not S3_AVAILABLE:
            raise ImportError("aioboto3 is required for S3 storage. Install with: pip install aioboto3")

        self.bucket_name = bucket_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name
        self.endpoint_url = endpoint_url
        self.public_endpoint_url = public_endpoint_url or endpoint_url
        self.session = aioboto3.Session()

    async def upload(
        self,
        file_content: bytes,
        destination_path: str,
        content_type: str,
        metadata: dict | None = None,
    ) -> str:
        """Upload file to S3."""
        async with self.session.client(
            "s3",
            region_name=self.region_name,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            endpoint_url=self.endpoint_url,
        ) as s3:
            await s3.put_object(
                Bucket=self.bucket_name,
                Key=destination_path,
                Body=file_content,
                ContentType=content_type,
                Metadata=metadata or {},
            )
        return destination_path

    async def download(self, file_path: str) -> bytes:
        """Download file from S3."""
        async with self.session.client(
            "s3",
            region_name=self.region_name,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            endpoint_url=self.endpoint_url,
        ) as s3:
            response = await s3.get_object(Bucket=self.bucket_name, Key=file_path)
            content: bytes = await response["Body"].read()
            return content

    async def delete(self, file_path: str) -> bool:
        """Delete file from S3."""
        async with self.session.client(
            "s3",
            region_name=self.region_name,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            endpoint_url=self.endpoint_url,
        ) as s3:
            try:
                await s3.delete_object(Bucket=self.bucket_name, Key=file_path)
                return True
            except ClientError:
                return False

    async def exists(self, file_path: str) -> bool:
        """Check if file exists in S3."""
        async with self.session.client(
            "s3",
            region_name=self.region_name,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            endpoint_url=self.endpoint_url,
        ) as s3:
            try:
                await s3.head_object(Bucket=self.bucket_name, Key=file_path)
                return True
            except ClientError:
                return False

    async def get_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Generate pre-signed URL for S3 object."""
        # Use public_endpoint_url for generating URLs accessible from browser
        # but use endpoint_url for the actual connection
        async with self.session.client(
            "s3",
            region_name=self.region_name,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            endpoint_url=self.public_endpoint_url,
        ) as s3:
            url: str = await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": file_path},
                ExpiresIn=expires_in,
            )
            return url

    async def get_available_space(self) -> int | None:
        """S3 has unlimited space (return None)."""
        return None
