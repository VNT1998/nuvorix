import datetime
from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict


class ArtifactMetadata(BaseModel):
    uri: str
    checksum_sha256: str
    content_type: str
    size_bytes: int
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class StorageBackend(ABC):
    """Abstract interface for artifact and model storage operations."""

    @abstractmethod
    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> ArtifactMetadata:
        """Upload binary artifact and return verified metadata with cryptographic checksum."""

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download binary artifact."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if artifact exists at given key."""

    @abstractmethod
    async def get_metadata(self, key: str) -> ArtifactMetadata | None:
        """Retrieve metadata for stored artifact without reading entire payload."""
