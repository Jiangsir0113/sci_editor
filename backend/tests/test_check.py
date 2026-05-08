from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

SAMPLE_DOCX_PATH = Path(__file__).parents[2] / "test1" / "未修改.docx"


async def _upload_doc(client):
    with open(SAMPLE_DOCX_PATH, "rb") as f:
        content = f.read()
    r = await client.post(
        "/api/upload",
        files={"file": ("test.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    return r.json()["doc_id"]


@pytest.mark.asyncio
async def test_check_returns_issues_and_diff():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        doc_id = await _upload_doc(client)
        response = await client.post(
            "/api/check",
            json={"doc_id": doc_id, "rule_filter": ["italics"]},
        )

    assert response.status_code == 200
    data = response.json()
    assert "issues" in data
    assert "diff" in data
    for entry in data["diff"]:
        assert "paragraph_index" in entry
        assert "original" in entry
        assert "modified" in entry
        assert "issue_ids" in entry
    # 如果有 issues，验证每条的必要字段
    for issue in data["issues"]:
        assert "issue_id" in issue
        assert "rule_id" in issue
        assert "severity" in issue
        assert "paragraph_index" in issue
        assert "fixable" in issue
    # 验证 diff 中的 issue_ids 都能在 issues 中找到对应条目
    issue_id_set = {i["issue_id"] for i in data["issues"]}
    for entry in data["diff"]:
        for iid in entry["issue_ids"]:
            assert iid in issue_id_set, f"diff.issue_id {iid} not found in issues"


@pytest.mark.asyncio
async def test_check_invalid_doc_id():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/check",
            json={"doc_id": "nonexistent-id", "rule_filter": ["italics"]},
        )
    assert response.status_code == 404
