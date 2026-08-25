import asyncio
import logging
from typing import Any
from uuid import UUID

from app.modules.analyses.repository import AnalysisRepository
from app.modules.analyses.schemas import AnalysisStatus, AnalysisType
from app.modules.media_forensics.image_analyzer import ImageAnalyzer
from app.modules.media_forensics.repository import MediaForensicsRepository
from app.modules.media_forensics.video_analyzer import VideoAnalyzer
from app.storage.base import StorageAdapter

logger = logging.getLogger(__name__)


class MediaForensicsService:
    def __init__(
        self,
        analysis_repository: AnalysisRepository,
        forensics_repository: MediaForensicsRepository,
        storage: StorageAdapter,
        image_analyzer: ImageAnalyzer,
        video_analyzer: VideoAnalyzer,
    ) -> None:
        self.analysis_repository = analysis_repository
        self.forensics_repository = forensics_repository
        self.storage = storage
        self.image_analyzer = image_analyzer
        self.video_analyzer = video_analyzer

    async def process_media(self, analysis_id: UUID) -> None:
        try:
            record = await self.analysis_repository.find_by_id(analysis_id)
            if not record or record.type not in (AnalysisType.IMAGE, AnalysisType.VIDEO):
                logger.warning(f"Analysis {analysis_id} is not an image or video.")
                return

            # Advance to PREPROCESSING
            await self.analysis_repository.update_status(
                analysis_id, 
                AnalysisStatus.PREPROCESSING, 
                progress=20
            )

            # Reconstruct the object key manually or rely on storage_path if possible.
            # But the prompt said: "Strictly resolve local/remote files through system-generated 
            # keys using the pattern analyses/{analysis_id}/input.{ext}"
            
            # For simplicity, we can parse the extension from original_file_name or mime_type.
            # But wait, StoredObject object_key is analyses/{analysis_id}/input.{ext}
            # The exact key can be inferred if we know the extension. The classifier saves the 
            # file and returns stored.object_key if it's available, but we only have 
            # `storage_path` in AnalysisRecord which could be local://analyses/x/input.jpg.
            
            # Let's extract object_key from storage_path
            if not record.storage_path:
                raise ValueError("No storage path found on analysis record.")
                
            object_key = record.storage_path.split("://", 1)[-1]
            if record.storage_path.startswith("supabase://"):
                # supabase://bucket/analyses/x/input.jpg -> bucket is first part
                object_key = object_key.split("/", 1)[-1]
                
            if not object_key.startswith(f"analyses/{analysis_id}/"):
                raise ValueError("Invalid object key derived from storage path.")

            # Load file bytes
            file_bytes = await self.storage.read(object_key)
            
            # Advance to ANALYZING
            await self.analysis_repository.update_status(
                analysis_id, 
                AnalysisStatus.ANALYZING, 
                progress=50
            )

            # Analyze based on type with timeout
            async def _analyze() -> Any:
                if record.type == AnalysisType.IMAGE:
                    return await self.image_analyzer.analyze(analysis_id, file_bytes)
                else:
                    return await self.video_analyzer.analyze(analysis_id, file_bytes)

            try:
                result = await asyncio.wait_for(_analyze(), timeout=30.0)
            except TimeoutError:
                logger.error(f"Analysis {analysis_id} timed out after 30 seconds.")
                await self.analysis_repository.update_status(
                    analysis_id,
                    AnalysisStatus.FAILED,
                    progress=0
                )
                return

            # Save results
            await self.forensics_repository.save_result(result)
            
            # Advance to COMPLETED (or next stage in lifecycle)
            await self.analysis_repository.update_status(
                analysis_id, 
                AnalysisStatus.COMPLETED, 
                progress=100
            )

        except Exception:
            logger.exception(f"Media processing failed for {analysis_id}")
            # FAILED state
            await self.analysis_repository.update_status(
                analysis_id, 
                AnalysisStatus.FAILED, 
                progress=0
            )
