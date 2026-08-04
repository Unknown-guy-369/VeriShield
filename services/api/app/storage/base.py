from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UploadPayload:
    analysis_id: UUID
    content: bytes
    extension: str
    mime_type: str

    @property
    def object_key(self) -> str:
        return f"analyses/{self.analysis_id}/input.{self.extension}"


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

    @abstractmethod
    async def read(self, object_key: str) -> bytes:
        raise NotImplementedError
