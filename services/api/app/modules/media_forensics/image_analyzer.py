import asyncio
import io
from typing import Any
from uuid import UUID

from PIL import ExifTags, Image

from app.modules.media_forensics.model_adapter import BaseModelAdapter
from app.modules.media_forensics.schemas import (
    MediaAnalysisResult,
)


class ImageAnalyzer:
    def __init__(self, model_adapter: BaseModelAdapter) -> None:
        self.model_adapter = model_adapter

    async def analyze(self, analysis_id: UUID, file_bytes: bytes) -> MediaAnalysisResult:
        # Preprocess the image and extract metadata
        preprocessed_bytes, metadata = await asyncio.wait_for(
            asyncio.to_thread(self._preprocess_and_extract_metadata, file_bytes),
            timeout=30.0
        )

        # Run inference via the model adapter
        prediction = await self.model_adapter.analyze_frame(preprocessed_bytes)

        # Map to MediaAnalysisResult
        return MediaAnalysisResult(
            analysis_id=analysis_id,
            media_type="IMAGE",
            manipulation_risk=prediction.manipulation_risk,
            confidence=prediction.confidence,
            model_version=prediction.model_version,
            findings=prediction.findings,
            suspicious_regions=prediction.suspicious_regions,
            metadata=metadata,
        )

    def _preprocess_and_extract_metadata(self, file_bytes: bytes) -> tuple[bytes, dict[str, Any]]:
        image = Image.open(io.BytesIO(file_bytes))
        metadata: dict[str, Any] = {}

        # 1. Extract EXIF
        exif_data = image.getexif()
        if exif_data:
            metadata["exif"] = {}
            for tag_id, value in exif_data.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                # Filter out raw bytes or huge fields for simplicity/safety
                if isinstance(value, (int, float, str)):
                    metadata["exif"][tag] = value
        else:
            metadata["exif"] = None

        # 2. Extract C2PA (Mocked for now as standard PIL doesn't support C2PA deeply)
        # In a real scenario, python-c2pa or c2patool bindings would be used here.
        metadata["c2pa_present"] = False

        # 3. Normalize dimensions to max 512x512 preserving aspect ratio
        image.thumbnail((512, 512), Image.Resampling.LANCZOS)
        
        # Convert to RGB (in case of RGBA or P)
        final_image: Any = image
        if image.mode != "RGB":
            final_image = image.convert("RGB")

        # Save to bytes
        out_io = io.BytesIO()
        final_image.save(out_io, format="JPEG", quality=95)
        preprocessed_bytes = out_io.getvalue()
        
        metadata["dimensions"] = {"width": image.width, "height": image.height}
        metadata["format"] = final_image.format or "JPEG"

        return preprocessed_bytes, metadata
