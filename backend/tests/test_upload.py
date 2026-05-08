import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from backend.main import app

SAMPLE_DOCX_PATH = Path(__file__).parents[2] / "test1" / "未修改.docx"


@pytest.mark.asyncio
async def test_upload_valid_docx():
    with open(SAMPLE_DOCX_PATH, "rb") as f:
        content = f.read()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/upload",
            files={"file": ("test.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )

    assert response.status_code == 200
    data = response.json()
    assert "doc_id" in data
    assert "paragraphs" in data
    assert len(data["paragraphs"]) > 0
    assert "available_rules" in data


@pytest.mark.asyncio
async def test_upload_wrong_format():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/upload",
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
    assert response.status_code == 400
