import asyncio

from supabase import Client, create_client

from app.storage.base import StorageAdapter, StoredObject, UploadPayload


class SupabaseStorageAdapter(StorageAdapter):
    def __init__(self, url: str, secret_key: str, bucket: str) -> None:
        self.client: Client = create_client(url, secret_key)
        self.bucket = bucket

    async def save(self, payload: UploadPayload) -> StoredObject:
        object_key = payload.object_key

        def upload() -> None:
            self.client.storage.from_(self.bucket).upload(
                path=object_key,
                file=payload.content,
                file_options={"content-type": payload.mime_type, "upsert": "false"},
            )

        await asyncio.to_thread(upload)
        return StoredObject(
            storage_path=f"supabase://{self.bucket}/{object_key}",
            object_key=object_key,
        )

    async def remove(self, stored: StoredObject) -> None:
        await asyncio.to_thread(
            self.client.storage.from_(self.bucket).remove,
            [stored.object_key],
        )

    async def read(self, object_key: str) -> bytes:
        def download() -> bytes:
            return self.client.storage.from_(self.bucket).download(object_key)
        return await asyncio.to_thread(download)
