import io
import uuid

import pytest
from PIL import Image

from app.modules.analyses.repository import MemoryAnalysisRepository
from app.modules.analyses.schemas import AnalysisStatus, AnalysisType, CreateAnalysisData
from app.modules.media_forensics.image_analyzer import ImageAnalyzer
from app.modules.media_forensics.model_adapter import MockModelAdapter
from app.modules.media_forensics.repository import MemoryMediaForensicsRepository
from app.modules.media_forensics.service import MediaForensicsService
from app.modules.media_forensics.video_analyzer import VideoAnalyzer
from app.storage.base import UploadPayload
from app.storage.local import LocalStorageAdapter


def create_valid_image_bytes() -> bytes:
    img = Image.new('RGB', (10, 10), color='red')
    out = io.BytesIO()
    img.save(out, format='JPEG')
    return out.getvalue()


def create_valid_video_bytes(tmp_path) -> bytes:
    import cv2
    import numpy as np
    
    path = str(tmp_path / "test.mp4")
    # For small tests without codecs, 'mp4v' works well locally for OpenCV
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(path, fourcc, 5, (64, 64))
    
    for _ in range(10):
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        frame.fill(255)
        out.write(frame)
        
    out.release()
    with open(path, "rb") as f:
        return f.read()


@pytest.fixture
def mock_storage(tmp_path):
    return LocalStorageAdapter(tmp_path)


@pytest.fixture
def test_dependencies(mock_storage):
    analysis_repo = MemoryAnalysisRepository()
    forensics_repo = MemoryMediaForensicsRepository()
    model_adapter = MockModelAdapter()
    image_analyzer = ImageAnalyzer(model_adapter)
    video_analyzer = VideoAnalyzer(model_adapter)
    service = MediaForensicsService(
        analysis_repository=analysis_repo,
        forensics_repository=forensics_repo,
        storage=mock_storage,
        image_analyzer=image_analyzer,
        video_analyzer=video_analyzer,
    )
    return service, analysis_repo, mock_storage, model_adapter


@pytest.mark.asyncio
async def test_image_preprocessing_valid(test_dependencies):
    service, repo, storage, _ = test_dependencies
    
    analysis_id = uuid.uuid4()
    await repo.create(CreateAnalysisData(
        id=analysis_id,
        type=AnalysisType.IMAGE,
        preferred_language="en",
        mime_type="image/jpeg",
        storage_path=f"local://analyses/{analysis_id}/input.jpg",
    ))
    
    payload = UploadPayload(
        analysis_id=analysis_id,
        content=create_valid_image_bytes(),
        extension="jpg",
        mime_type="image/jpeg"
    )
    await storage.save(payload)
    
    await service.process_media(analysis_id)
    
    record = await repo.find_by_id(analysis_id)
    assert record.status == AnalysisStatus.COMPLETED
    assert record.progress == 100


@pytest.mark.asyncio
async def test_image_preprocessing_invalid(test_dependencies):
    service, repo, storage, _ = test_dependencies
    
    analysis_id = uuid.uuid4()
    await repo.create(CreateAnalysisData(
        id=analysis_id,
        type=AnalysisType.IMAGE,
        preferred_language="en",
        mime_type="image/jpeg",
        storage_path=f"local://analyses/{analysis_id}/input.jpg",
    ))
    
    payload = UploadPayload(
        analysis_id=analysis_id,
        content=b"not an image",
        extension="jpg",
        mime_type="image/jpeg"
    )
    await storage.save(payload)
    
    await service.process_media(analysis_id)
    
    record = await repo.find_by_id(analysis_id)
    assert record.status == AnalysisStatus.FAILED
    assert record.progress == 0


@pytest.mark.asyncio
async def test_video_sampling(test_dependencies, tmp_path):
    service, repo, storage, _ = test_dependencies
    
    analysis_id = uuid.uuid4()
    await repo.create(CreateAnalysisData(
        id=analysis_id,
        type=AnalysisType.VIDEO,
        preferred_language="en",
        mime_type="video/mp4",
        storage_path=f"local://analyses/{analysis_id}/input.mp4",
    ))
    
    payload = UploadPayload(
        analysis_id=analysis_id,
        content=create_valid_video_bytes(tmp_path),
        extension="mp4",
        mime_type="video/mp4"
    )
    await storage.save(payload)
    
    await service.process_media(analysis_id)
    
    record = await repo.find_by_id(analysis_id)
    assert record.status == AnalysisStatus.COMPLETED
    assert record.progress == 100


@pytest.mark.asyncio
async def test_video_invalid(test_dependencies):
    service, repo, storage, _ = test_dependencies
    
    analysis_id = uuid.uuid4()
    await repo.create(CreateAnalysisData(
        id=analysis_id,
        type=AnalysisType.VIDEO,
        preferred_language="en",
        mime_type="video/mp4",
        storage_path=f"local://analyses/{analysis_id}/input.mp4",
    ))
    
    payload = UploadPayload(
        analysis_id=analysis_id,
        content=b"not a video",
        extension="mp4",
        mime_type="video/mp4"
    )
    await storage.save(payload)
    
    await service.process_media(analysis_id)
    
    record = await repo.find_by_id(analysis_id)
    assert record.status == AnalysisStatus.FAILED
    assert record.progress == 0


@pytest.mark.asyncio
async def test_model_adapter_mock():
    # Deterministic fake adapter
    adapter = MockModelAdapter()
    image_bytes = create_valid_image_bytes()
    
    prediction = await adapter.analyze_frame(image_bytes)
    assert prediction.manipulation_risk >= 0.0
    assert prediction.model_version == "mock-adapter/1.0"
    
    # Analyze multiple frames
    predictions = await adapter.analyze_frames([image_bytes, image_bytes])
    assert len(predictions) == 2
    assert predictions[0].manipulation_risk == predictions[1].manipulation_risk


@pytest.mark.asyncio
async def test_service_lifecycle_transitions(test_dependencies):
    service, repo, storage, _ = test_dependencies
    
    analysis_id = uuid.uuid4()
    await repo.create(CreateAnalysisData(
        id=analysis_id,
        type=AnalysisType.IMAGE,
        preferred_language="en",
        mime_type="image/jpeg",
        storage_path=f"local://analyses/{analysis_id}/input.jpg",
    ))
    
    payload = UploadPayload(
        analysis_id=analysis_id,
        content=create_valid_image_bytes(),
        extension="jpg",
        mime_type="image/jpeg"
    )
    await storage.save(payload)
    
    # We can mock the image_analyzer.analyze to check intermediate states
    class MockAnalyzer:
        async def analyze(self, a_id, b):
            record = await repo.find_by_id(a_id)
            assert record.status == AnalysisStatus.ANALYZING
            assert record.progress == 50
            from app.modules.media_forensics.schemas import ConfidenceLevel, MediaAnalysisResult
            return MediaAnalysisResult(
                analysis_id=a_id,
                media_type="IMAGE",
                manipulation_risk=0.5,
                confidence=ConfidenceLevel.MEDIUM,
                model_version="mock",
                findings=[],
                metadata={}
            )
            
    service.image_analyzer = MockAnalyzer()
    
    initial = await repo.find_by_id(analysis_id)
    assert initial.status == AnalysisStatus.QUEUED
    
    await service.process_media(analysis_id)
    
    final = await repo.find_by_id(analysis_id)
    assert final.status == AnalysisStatus.COMPLETED
    assert final.progress == 100
