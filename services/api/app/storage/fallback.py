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

    async def remove(self, stored: StoredObject) -> None:
        adapter = self.primary if stored.storage_path.startswith("supabase://") else self.fallback
        await adapter.remove(stored)
