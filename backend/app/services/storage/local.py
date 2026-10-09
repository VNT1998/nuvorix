import asyncio
import datetime
import hashlib
import os

from backend.app.core.config import settings
from backend.app.services.storage.base import ArtifactMetadata, StorageBackend


class LocalFileSystemStorage(StorageBackend):
    """Local filesystem storage implementation for single-node development and testing."""

    def __init__(self, base_path: str | None = None):
        self.base_path = base_path or settings.ARTIFACT_STORE_PATH
        os.makedirs(self.base_path, exist_ok=True)

    def _resolve_path(self, key: str) -> str:
        # Sanitize path to prevent directory traversal
        clean_key = os.path.normpath(key).lstrip("/\\")
        return os.path.join(self.base_path, clean_key)

    def _write_file(self, target_path: str, data: bytes) -> None:
        with open(target_path, "wb") as f:
            f.write(data)

    def _read_file(self, target_path: str) -> bytes:
        with open(target_path, "rb") as f:
            return f.read()

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> ArtifactMetadata:
        target_path = self._resolve_path(key)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        checksum = hashlib.sha256(data).hexdigest()
        await asyncio.to_thread(self._write_file, target_path, data)

        stat = os.stat(target_path)
        return ArtifactMetadata(
            uri=f"file://{os.path.abspath(target_path)}",
            checksum_sha256=checksum,
            content_type=content_type,
            size_bytes=stat.st_size,
            created_at=datetime.datetime.now(datetime.UTC),
        )

    async def download(self, key: str) -> bytes:
        target_path = self._resolve_path(key)
        if not os.path.exists(target_path):
            raise FileNotFoundError(f"Artifact at key '{key}' not found on local storage.")
        return await asyncio.to_thread(self._read_file, target_path)

    async def exists(self, key: str) -> bool:
        target_path = self._resolve_path(key)
        return os.path.exists(target_path)

    async def get_metadata(self, key: str) -> ArtifactMetadata | None:
        target_path = self._resolve_path(key)
        if not os.path.exists(target_path):
            return None

        stat = os.stat(target_path)
        data = await asyncio.to_thread(self._read_file, target_path)
        checksum = hashlib.sha256(data).hexdigest()

        return ArtifactMetadata(
            uri=f"file://{os.path.abspath(target_path)}",
            checksum_sha256=checksum,
            content_type="application/octet-stream",
            size_bytes=stat.st_size,
            created_at=datetime.datetime.fromtimestamp(stat.st_mtime, tz=datetime.UTC),
        )
