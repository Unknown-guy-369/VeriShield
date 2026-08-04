import tempfile
from typing import Any
from uuid import UUID

import anyio

from app.modules.media_forensics.model_adapter import BaseModelAdapter
from app.modules.media_forensics.schemas import (
    ConfidenceLevel,
    Finding,
    MediaAnalysisResult,
    SeverityLevel,
    Timestamp,
)


class VideoAnalyzer:
    MAX_FRAMES = 15

    def __init__(self, model_adapter: BaseModelAdapter) -> None:
        self.model_adapter = model_adapter

    async def analyze(self, analysis_id: UUID, file_bytes: bytes) -> MediaAnalysisResult:
        # We need a temp file for OpenCV to read video
        temp_fd, temp_path = tempfile.mkstemp(suffix=".mp4")
        try:
            async with await anyio.open_file(temp_path, "wb") as f:
                await f.write(file_bytes)

            # Extract frames safely
            frames, timestamps, metadata = await anyio.to_thread.run_sync(
                self._extract_frames, temp_path
            )

            # Analyze frames
            predictions = await self.model_adapter.analyze_frames(frames)
            
            # Aggregate scores
            if not predictions:
                raise ValueError("No frames extracted from video")

            total_risk = sum(p.manipulation_risk for p in predictions)
            avg_risk = total_risk / len(predictions)
            
            suspicious_timestamps = []
            findings = []
            
            for i, p in enumerate(predictions):
                if p.manipulation_risk > 0.7:
                    suspicious_timestamps.append(
                        Timestamp(start_seconds=timestamps[i], end_seconds=timestamps[i]+0.5)
                    )
            
            if avg_risk > 0.5:
                findings.append(
                    Finding(
                        code="AGGREGATED_VIDEO_RISK",
                        severity=SeverityLevel.HIGH if avg_risk > 0.8 else SeverityLevel.MEDIUM,
                        score=avg_risk,
                        explanation=f"Video risk aggregated from {len(predictions)} frames."
                    )
                )

            return MediaAnalysisResult(
                analysis_id=analysis_id,
                media_type="VIDEO",
                manipulation_risk=avg_risk,
                confidence=ConfidenceLevel.MEDIUM,
                model_version=predictions[0].model_version if predictions else "unknown",
                findings=findings,
                suspicious_timestamps=suspicious_timestamps,
                metadata=metadata,
            )

        finally:
            # Aggressive temporary file cleanup
            file_path = anyio.Path(temp_path)
            if await file_path.exists():
                try:
                    await file_path.unlink()
                except OSError:
                    pass

    def _extract_frames(self, video_path: str) -> tuple[list[bytes], list[float], dict[str, Any]]:
        import cv2

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("Failed to decode video file.")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0

        metadata = {
            "fps": fps,
            "total_frames": total_frames,
            "duration_seconds": duration,
            "dimensions": {"width": width, "height": height},
        }

        # Adaptive bounded sampling
        frames: list[bytes] = []
        timestamps: list[float] = []
        
        # Calculate interval to get at most MAX_FRAMES
        interval = max(1, total_frames // self.MAX_FRAMES)
        
        count = 0
        while cap.isOpened() and len(frames) < self.MAX_FRAMES:
            ret, frame = cap.read()
            if not ret:
                break
                
            if count % interval == 0:
                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Resize keeping aspect ratio for model uniformity (512x512)
                h, w = rgb_frame.shape[:2]
                scale = min(512/w, 512/h)
                new_w, new_h = int(w * scale), int(h * scale)
                resized = cv2.resize(rgb_frame, (new_w, new_h))
                
                # Encode to bytes (jpeg)
                _, buffer = cv2.imencode('.jpg', cv2.cvtColor(resized, cv2.COLOR_RGB2BGR))
                
                frames.append(buffer.tobytes())
                
                # Calculate timestamp
                timestamp = count / fps if fps > 0 else 0
                timestamps.append(timestamp)
                
            count += 1
            
        cap.release()
        return frames, timestamps, metadata
