import asyncio
import hashlib
from abc import ABC, abstractmethod
from typing import Any

from app.modules.media_forensics.schemas import (
    ConfidenceLevel,
    Finding,
    Region,
    SeverityLevel,
)


class ModelPrediction:
    def __init__(
        self,
        manipulation_risk: float,
        confidence: ConfidenceLevel,
        model_version: str,
        findings: list[Finding] | None = None,
        suspicious_regions: list[Region] | None = None,
    ) -> None:
        self.manipulation_risk = manipulation_risk
        self.confidence = confidence
        self.model_version = model_version
        self.findings = findings or []
        self.suspicious_regions = suspicious_regions or []


class BaseModelAdapter(ABC):
    @abstractmethod
    async def analyze_frame(self, frame_bytes: bytes) -> ModelPrediction:
        """Analyzes a single frame/image and returns a prediction."""
        raise NotImplementedError

    @abstractmethod
    async def analyze_frames(self, frames: list[bytes]) -> list[ModelPrediction]:
        """Analyzes a sequence of frames and returns predictions."""
        raise NotImplementedError


class MockModelAdapter(BaseModelAdapter):
    """
    Deterministic mock adapter mapping file hashes to static outputs.
    """
    def __init__(self) -> None:
        self.version = "mock-adapter/1.0"

    async def analyze_frame(self, frame_bytes: bytes) -> ModelPrediction:
        def _mock_inference() -> ModelPrediction:
            # Deterministic hash to simulate varied results
            file_hash = hashlib.sha256(frame_bytes).hexdigest()
            hash_int = int(file_hash[:8], 16)
            
            # Simple pseudo-random logic based on file contents
            risk = (hash_int % 100) / 100.0
            
            confidence = ConfidenceLevel.HIGH
            findings = []
            regions = []
            
            if risk > 0.7:
                confidence = ConfidenceLevel.MEDIUM
                findings.append(
                    Finding(
                        code="SPATIAL_ANOMALY",
                        severity=SeverityLevel.HIGH,
                        score=risk,
                        explanation="Detected spatial inconsistencies typical of AI generation."
                    )
                )
                # Mock region
                regions.append(Region(x_min=0.1, y_min=0.2, x_max=0.4, y_max=0.5))
                
            return ModelPrediction(
                manipulation_risk=risk,
                confidence=confidence,
                model_version=self.version,
                findings=findings,
                suspicious_regions=regions,
            )

        # Ensure we don't block the event loop, even for mocking (simulating delay)
        await asyncio.sleep(0.1) 
        return await asyncio.to_thread(_mock_inference)

    async def analyze_frames(self, frames: list[bytes]) -> list[ModelPrediction]:
        # Process sequentially or in parallel depending on needs. We mock it sequentially.
        return [await self.analyze_frame(f) for f in frames]


class ONNXModelAdapter(BaseModelAdapter):
    """
    Lightweight ONNX runtime adapter for vit-base-patch16-224-in21k or similar.
    """
    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        self.version = "onnx-vit-base/1.0"
        self._session = None
        
    def _load_model(self) -> Any:
        import onnxruntime as ort  # type: ignore[import-untyped]
        if self._session is None:
            # CPU Execution provider for safety and broad compatibility
            self._session = ort.InferenceSession(
                self.model_path, 
                providers=["CPUExecutionProvider"]
            )
        return self._session

    def _preprocess(self, frame_bytes: bytes) -> Any:
        import io

        import numpy as np
        from PIL import Image
        
        # Open and resize strictly to 224x224 for ViT models, normalized
        image = Image.open(io.BytesIO(frame_bytes)).convert("RGB")
        image = image.resize((224, 224))
        
        # Convert to numpy and normalize (ImageNet stats)
        img_array = np.array(image).astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406])
        std = np.array([0.229, 0.224, 0.225])
        img_array = (img_array - mean) / std
        
        # HWC to CHW format for PyTorch/ONNX standard
        img_array = np.transpose(img_array, (2, 0, 1))
        # Add batch dimension
        return np.expand_dims(img_array, axis=0)

    async def analyze_frame(self, frame_bytes: bytes) -> ModelPrediction:
        def _inference() -> ModelPrediction:
            session = self._load_model()
            input_data = self._preprocess(frame_bytes)
            
            input_name = session.get_inputs()[0].name
            output_name = session.get_outputs()[0].name
            
            # Run inference
            result = session.run([output_name], {input_name: input_data})[0]
            
            # Assuming output is logits for [real, fake]
            import numpy as np
            # Softmax to get probability
            exp_preds = np.exp(result[0])
            probs = exp_preds / np.sum(exp_preds)
            fake_prob = float(probs[1]) if len(probs) > 1 else float(probs[0])
            
            findings = []
            if fake_prob > 0.5:
                findings.append(
                    Finding(
                        code="MODEL_CLASSIFICATION",
                        severity=SeverityLevel.HIGH if fake_prob > 0.8 else SeverityLevel.MEDIUM,
                        score=fake_prob,
                        explanation=(
                            "The ONNX ViT model classified this image as likely manipulated."
                        )
                    )
                )

            return ModelPrediction(
                manipulation_risk=fake_prob,
                confidence=ConfidenceLevel.MEDIUM,
                model_version=self.version,
                findings=findings,
            )

        # Enforce timeout for synchronous model inference to protect event loop
        return await asyncio.wait_for(asyncio.to_thread(_inference), timeout=30.0)

    async def analyze_frames(self, frames: list[bytes]) -> list[ModelPrediction]:
        # Process sequentially to avoid memory spikes, but wrapped in asyncio.gather if parallel.
        # For CPU bounds, sequential is safer.
        predictions = []
        for frame in frames:
            predictions.append(await self.analyze_frame(frame))
        return predictions

