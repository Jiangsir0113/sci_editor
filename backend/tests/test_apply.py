from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

SAMPLE_DOCX_PATH = Path(__file__).parents[2] / "test1" / "未修改.docx"


async def _upload_and_check(client):
    with open(SAMPLE_DOCX_PATH, "rb") as f:
        content = f.read()
    r = await client.post(
        "/api/upload",
        files={"file": ("test.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    doc_id = r.json()["doc_id"]

    r2 = await client.post(
        "/api/check",
        json={"doc_id": doc_id, "rule_filter": ["italics"]},
    )
    issues = r2.json()["issues"]
    return doc_id, issues


@pytest.mark.asyncio
async def test_apply_returns_docx():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        doc_id, issues = await _upload_and_check(client)
        decisions = [
            {"issue_id": i["issue_id"], "action": "accept"}
            for i in issues[:3]
        ] if issues else []
        response = await client.post(
            "/api/apply",
            json={"doc_id": doc_id, "decisions": decisions},
        )

    assert response.status_code == 200
    assert "wordprocessingml" in response.headers["content-type"]
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_apply_invalid_doc_id():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/apply",
            json={"doc_id": "bad-id", "decisions": []},
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_apply_empty_decisions_returns_docx():
    """无任何决策时，直接返回原始文档（不修改）"""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        doc_id, _ = await _upload_and_check(client)
        response = await client.post(
            "/api/apply",
            json={"doc_id": doc_id, "decisions": []},
        )
    assert response.status_code == 200
    assert len(response.content) > 0
