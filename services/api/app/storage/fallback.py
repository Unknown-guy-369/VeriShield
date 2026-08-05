import httpx

from app.storage.base import StorageAdapter, StoredObject, UploadPayload


class FallbackStorageAdapter(StorageAdapter):
    """Uses local storage only when Supabase has a transient transport failure."""

    def __init__(self, primary: StorageAdapter, fallback: StorageAdapter) -> None:
        self.primary = primary
        self.fallback = fallback

    async def save(self, payload: UploadPayload) -> StoredObject:
        try:
            return await self.primary.save(payload)
        except httpx.TransportError:
            return await self.fallback.save(payload)

    async def read(self, object_key: str) -> bytes:
        try:
            return await self.primary.read(object_key)
        except Exception:
            return await self.fallback.read(object_key)

    async def remove(self, stored: StoredObject) -> None:
        adapter = self.primary if stored.storage_path.startswith("supabase://") else self.fallback
        await adapter.remove(stored)
