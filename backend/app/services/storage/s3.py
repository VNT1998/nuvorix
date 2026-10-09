import datetime
import hashlib
import logging
from typing import Any

from backend.app.services.storage.base import ArtifactMetadata, StorageBackend

logger = logging.getLogger(__name__)


class S3CompatibleStorage(StorageBackend):
    """
    S3-compatible object storage backend (AWS S3, MinIO, Cloudflare R2).
    Requires configured bucket and endpoint for multi-replica production environments.
    """

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        region_name: str = "us-east-1",
    ):
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region_name = region_name
        self._s3_client: Any = None

    def _get_client(self) -> Any:
        if self._s3_client is None:
            try:
                import boto3  # type: ignore[import-not-found]

                kwargs: dict[str, Any] = {"region_name": self.region_name}
                if self.endpoint_url:
                    kwargs["endpoint_url"] = self.endpoint_url
                if self.access_key_id and self.secret_access_key:
                    kwargs["aws_access_key_id"] = self.access_key_id
                    kwargs["aws_secret_access_key"] = self.secret_access_key

                self._s3_client = boto3.client("s3", **kwargs)
            except ImportError as err:
                raise RuntimeError(
                    "boto3 package required for S3CompatibleStorage in production. "
                    "Install with `uv add boto3` or configure local storage."
                ) from err
        return self._s3_client

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> ArtifactMetadata:
        checksum = hashlib.sha256(data).hexdigest()
        client = self._get_client()

        client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
            Metadata={"sha256": checksum},
        )

        return ArtifactMetadata(
            uri=f"s3://{self.bucket_name}/{key}",
            checksum_sha256=checksum,
            content_type=content_type,
            size_bytes=len(data),
            created_at=datetime.datetime.now(datetime.UTC),
        )

    async def download(self, key: str) -> bytes:
        client = self._get_client()
        try:
            resp = client.get_object(Bucket=self.bucket_name, Key=key)
            return resp["Body"].read()
        except Exception as e:
            raise FileNotFoundError(
                f"S3 object '{key}' not found in bucket '{self.bucket_name}': {e}"
            ) from e

    async def exists(self, key: str) -> bool:
        client = self._get_client()
        try:
            client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    async def get_metadata(self, key: str) -> ArtifactMetadata | None:
        client = self._get_client()
        try:
            head = client.head_object(Bucket=self.bucket_name, Key=key)
            checksum = head.get("Metadata", {}).get("sha256", head.get("ETag", "").strip('"'))
            return ArtifactMetadata(
                uri=f"s3://{self.bucket_name}/{key}",
                checksum_sha256=checksum,
                content_type=head.get("ContentType", "application/octet-stream"),
                size_bytes=head.get("ContentLength", 0),
                created_at=head.get("LastModified", datetime.datetime.now(datetime.UTC)),
            )
        except Exception:
            return None
