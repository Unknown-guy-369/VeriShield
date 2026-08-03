from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.database.session import is_supabase_transaction_pooler, normalize_database_url
from app.main import create_app


def create_test_client(tmp_path: Path) -> TestClient:
    settings = Settings(
        database_url=None,
        supabase_url=None,
        supabase_secret_key=None,
        local_upload_dir=tmp_path / "uploads",
    )
    return TestClient(create_app(settings))


def test_reports_service_health(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["persistence"] == "memory"


def test_creates_and_retrieves_text_analysis(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        created = client.post(
            "/api/v1/analyses",
            json={
                "input": "A complete claim that should be checked against reliable sources.",
                "preferredLanguage": "en",
            },
        )
        fetched = client.get(f"/api/v1/analyses/{created.json()['id']}")

    assert created.status_code == 201
    assert created.json()["type"] == "TEXT"
    assert created.json()["status"] == "QUEUED"
    assert created.json()["progress"] == 10
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created.json()["id"]


def test_classifies_public_url_without_user_selected_type(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        response = client.post(
            "/api/v1/analyses",
            json={"input": "https://example.com/public-post", "preferredLanguage": "en"},
        )

    assert response.status_code == 201
    assert response.json()["type"] == "URL"
    assert response.json()["sourceUrl"] == "https://example.com/public-post"


def test_rejects_empty_and_short_unattached_input(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        missing_input = client.post(
            "/api/v1/analyses",
            json={"preferredLanguage": "en"},
        )
        short_input = client.post(
            "/api/v1/analyses",
            json={"input": "short", "preferredLanguage": "en"},
        )

    assert missing_input.status_code == 400
    assert missing_input.json()["code"] == "INPUT_REQUIRED"
    assert short_input.status_code == 400
    assert short_input.json()["code"] == "INPUT_TOO_SHORT"


def test_accepts_signature_valid_png_upload(tmp_path: Path) -> None:
    png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    with create_test_client(tmp_path) as client:
        response = client.post(
            "/api/v1/analyses",
            data={
                "input": "Check whether this image was manipulated.",
                "preferredLanguage": "en",
            },
            files={"file": ("sample.png", png, "image/png")},
        )

    assert response.status_code == 201
    assert response.json()["type"] == "IMAGE"
    assert response.json()["text"] == "Check whether this image was manipulated."
    assert response.json()["mimeType"] == "image/png"
    assert response.json()["storagePath"] == (
        f"local://analyses/{response.json()['id']}/input.png"
    )


def test_rejects_mismatched_media_content(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        response = client.post(
            "/api/v1/analyses",
            data={"input": "Check this attachment", "preferredLanguage": "en"},
            files={"file": ("fake.png", b"not an image", "image/png")},
        )
    assert response.status_code == 400
    assert response.json()["code"] == "UNSUPPORTED_MEDIA"


def test_returns_clean_not_found_response(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        response = client.get("/api/v1/analyses/11111111-1111-4111-8111-111111111111")
    assert response.status_code == 404
    assert response.json()["code"] == "ANALYSIS_NOT_FOUND"


def test_supabase_prisma_pooler_url_is_compatible_with_psycopg() -> None:
    url = (
        "postgresql://postgres.project:password@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"
        "?pgbouncer=true&sslmode=require"
    )

    normalized = normalize_database_url(url)

    assert normalized.startswith("postgresql+psycopg://")
    assert "pgbouncer" not in normalized
    assert "sslmode=require" in normalized
    assert is_supabase_transaction_pooler(normalized)
