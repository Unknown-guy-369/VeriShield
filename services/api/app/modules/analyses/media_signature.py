from dataclasses import dataclass

from app.core.errors import AppError


@dataclass(frozen=True, slots=True)
class DetectedMedia:
    mime_type: str
    extension: str


def detect_media_signature(content: bytes) -> DetectedMedia:
    if content.startswith(b"\xff\xd8\xff"):
        return DetectedMedia("image/jpeg", "jpg")
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return DetectedMedia("image/png", "png")
    if content.startswith((b"GIF87a", b"GIF89a")):
        return DetectedMedia("image/gif", "gif")
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return DetectedMedia("image/webp", "webp")
    if content.startswith(b"\x1aE\xdf\xa3"):
        return DetectedMedia("video/webm", "webm")
    if len(content) >= 12 and content[4:8] == b"ftyp":
        if content[8:12] == b"qt  ":
            return DetectedMedia("video/quicktime", "mov")
        return DetectedMedia("video/mp4", "mp4")
    raise AppError(400, "UNSUPPORTED_MEDIA", "The uploaded file has an unsupported signature.")
