import asyncio
from pathlib import Path

from app.storage.base import StorageAdapter, StoredObject, UploadPayload


class LocalStorageAdapter(StorageAdapter):
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    async def save(self, payload: UploadPayload) -> StoredObject:
        object_key = payload.object_key
        target = self.root / object_key
        await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(target.write_bytes, payload.content)
        return StoredObject(storage_path=f"local://{object_key}", object_key=object_key)

    async def remove(self, stored: StoredObject) -> None:
        target = self.root / stored.object_key
        await asyncio.to_thread(target.unlink, missing_ok=True)

    async def read(self, object_key: str) -> bytes:
        target = self.root / object_key
        if not str(target.resolve()).startswith(str(self.root.resolve())):
            raise ValueError("Path traversal attempt detected")
        return await asyncio.to_thread(target.read_bytes)
