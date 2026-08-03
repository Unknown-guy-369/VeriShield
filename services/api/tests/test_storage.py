from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from app.storage.base import StorageAdapter, StoredObject, UploadPayload
from app.storage.fallback import FallbackStorageAdapter
from app.storage.local import LocalStorageAdapter


class UnavailableStorageAdapter(StorageAdapter):
    async def save(self, payload: UploadPayload) -> StoredObject:
        raise httpx.ReadError("Temporary read failure", request=httpx.Request("PUT", "https://example.com"))

    async def remove(self, stored: StoredObject) -> None:
        raise AssertionError("The unavailable primary adapter should not remove fallback files.")


@pytest.mark.asyncio
async def test_falls_back_to_local_storage_on_transport_error(tmp_path: Path) -> None:
    storage = FallbackStorageAdapter(
        primary=UnavailableStorageAdapter(),
        fallback=LocalStorageAdapter(tmp_path / "uploads"),
    )
    analysis_id = uuid4()
    payload = UploadPayload(
        analysis_id=analysis_id,
        content=b"test image",
        extension="png",
        mime_type="image/png",
    )

    stored = await storage.save(payload)

    assert stored.storage_path == f"local://analyses/{analysis_id}/input.png"
    await storage.remove(stored)
