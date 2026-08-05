import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.storage.base import UploadPayload
from app.storage.local import LocalStorageAdapter
from app.storage.supabase import SupabaseStorageAdapter


@pytest.mark.asyncio
async def test_local_storage_reads(tmp_path: Path) -> None:
    adapter = LocalStorageAdapter(tmp_path)
    payload = UploadPayload(
        analysis_id=uuid.uuid4(),
        content=b"test content",
        extension="txt",
        mime_type="text/plain",
    )
    
    stored = await adapter.save(payload)
    assert stored.object_key == payload.object_key
    assert stored.storage_path == f"local://{payload.object_key}"
    
    content = await adapter.read(stored.object_key)
    assert content == b"test content"
    
    await adapter.remove(stored)
    with pytest.raises(FileNotFoundError):
        await adapter.read(stored.object_key)


@pytest.mark.asyncio
async def test_supabase_storage_reads() -> None:
    with patch("app.storage.supabase.create_client") as mock_create_client:
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        mock_storage = MagicMock()
        mock_client.storage.from_.return_value = mock_storage
        
        mock_storage.download.return_value = b"supabase content"
        
        adapter = SupabaseStorageAdapter("http://localhost", "secret", "test-bucket")
        
        content = await adapter.read("analyses/test/input.jpg")
        
        assert content == b"supabase content"
        mock_storage.download.assert_called_once_with("analyses/test/input.jpg")
