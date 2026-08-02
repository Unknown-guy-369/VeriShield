from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UploadPayload:
    content: bytes
    extension: str
    mime_type: str


@dataclass(frozen=True, slots=True)
class StoredObject:
    storage_path: str
    object_key: str


class StorageAdapter(ABC):
    @abstractmethod
    async def save(self, payload: UploadPayload) -> StoredObject:
        raise NotImplementedError

    @abstractmethod
    async def remove(self, stored: StoredObject) -> None:
        raise NotImplementedError
