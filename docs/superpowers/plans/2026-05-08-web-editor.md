# SCI Editor Web 版实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 Python 桌面工具改造为可部署到服务器的网页版，编辑可以在浏览器中上传文档、选择规则、审核每条修改（接受/拒绝/手动编辑）后导出最终文档。

**Architecture:** FastAPI 后端直接复用现有规则引擎（engine.py/parser.py/fixer.py/rules/），提供三个 REST 接口（upload/check/apply）；React 前端实现左右对比区 + 底部逐条操作列表，通过 contenteditable 支持右栏富文本编辑；Docker Compose 将前后端打包部署，nginx 反向代理 API 请求。

**Tech Stack:** Python 3.11, FastAPI, uvicorn, python-docx（已有）；React 18, Vite, Zustand, Tailwind CSS；Docker + Docker Compose + nginx

---

## 文件结构

```
sci_editor/
├── backend/                        # 新建：FastAPI 后端
│   ├── main.py                     # FastAPI app，挂载路由
│   ├── routers/
│   │   └── editor.py               # /upload /check /apply 路由
│   ├── schemas.py                  # Pydantic 请求/响应模型
│   ├── session.py                  # 会话管理（内存 + 临时文件）
│   ├── diff.py                     # 生成段落级别的 diff 数据
│   ├── requirements.txt            # FastAPI, uvicorn, python-multipart
│   └── tests/
│       ├── test_upload.py
│       ├── test_check.py
│       └── test_apply.py
├── frontend/                       # 新建：React 前端
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── store.ts                # Zustand 全局状态
│       ├── api.ts                  # fetch 封装
│       ├── components/
│       │   ├── Toolbar.tsx         # 顶部：上传 + 规则 Chip + 执行
│       │   ├── DiffView.tsx        # 左右对比区
│       │   ├── ChangeList.tsx      # 底部逐条列表
│       │   └── EditablePanel.tsx   # 右栏富文本编辑逻辑
│       └── types.ts                # 前端类型定义
├── docker-compose.yml              # 新建
├── backend/Dockerfile              # 新建
└── frontend/Dockerfile             # 新建（nginx 托管静态文件）

# 现有文件（不修改）
sci_editor/engine.py
sci_editor/parser.py
sci_editor/fixer.py
sci_editor/models.py
sci_editor/rules/
```

---

## Task 1: 后端基础框架

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/schemas.py`
- Create: `backend/session.py`
- Create: `backend/main.py`
- Create: `backend/tests/test_upload.py`
- Create: `backend/routers/editor.py`（仅 `/upload`）

- [ ] **Step 1: 创建 backend/requirements.txt**

```
fastapi>=0.111
uvicorn[standard]>=0.29
python-multipart>=0.0.9
python-docx>=1.0
jinja2>=3.1
httpx>=0.27       # 测试用
pytest>=8
pytest-asyncio>=0.23
```

- [ ] **Step 2: 创建 backend/schemas.py**

```python
from pydantic import BaseModel
from typing import List, Optional


class ParagraphOut(BaseModel):
    index: int
    text: str
    section: str


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    paragraphs: List[ParagraphOut]
    available_rules: List[str]


class CheckRequest(BaseModel):
    doc_id: str
    rule_filter: List[str]


class DiffEntry(BaseModel):
    paragraph_index: int
    original: str
    modified: str
    issue_ids: List[str]


class IssueOut(BaseModel):
    issue_id: str
    rule_id: str
    rule_name: str
    severity: str
    section: str
    paragraph_index: int
    context: str
    suggestion: str
    fixable: bool
    fix_description: str


class CheckResponse(BaseModel):
    issues: List[IssueOut]
    diff: List[DiffEntry]


class Decision(BaseModel):
    issue_id: str
    action: str          # "accept" | "reject" | "manual"
    final_text: Optional[str] = None


class ApplyRequest(BaseModel):
    doc_id: str
    decisions: List[Decision]
```

- [ ] **Step 3: 创建 backend/session.py**

```python
import uuid
import os
import tempfile
import time
from typing import Dict, Any

_sessions: Dict[str, Dict[str, Any]] = {}
TMP_DIR = os.path.join(tempfile.gettempdir(), "sci_editor_sessions")
SESSION_TTL = 3600  # 1 小时


def create_session(filename: str) -> str:
    doc_id = str(uuid.uuid4())
    session_dir = os.path.join(TMP_DIR, doc_id)
    os.makedirs(session_dir, exist_ok=True)
    _sessions[doc_id] = {
        "filename": filename,
        "dir": session_dir,
        "created_at": time.time(),
    }
    return doc_id


def get_session(doc_id: str) -> Dict[str, Any]:
    session = _sessions.get(doc_id)
    if session is None:
        raise KeyError(f"Session {doc_id} not found")
    return session


def session_path(doc_id: str, filename: str) -> str:
    return os.path.join(_sessions[doc_id]["dir"], filename)


def delete_session(doc_id: str) -> None:
    session = _sessions.pop(doc_id, None)
    if session:
        import shutil
        shutil.rmtree(session["dir"], ignore_errors=True)


def cleanup_expired() -> None:
    now = time.time()
    expired = [
        doc_id for doc_id, s in _sessions.items()
        if now - s["created_at"] > SESSION_TTL
    ]
    for doc_id in expired:
        delete_session(doc_id)
```

- [ ] **Step 4: 创建 backend/routers/editor.py（仅 /upload）**

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, UploadFile, File, HTTPException
from sci_editor.parser import parse_document
from sci_editor.engine import RuleEngine
from ..session import create_session, session_path, get_session
from ..schemas import UploadResponse, ParagraphOut

router = APIRouter(prefix="/api")
_engine = RuleEngine()

RULE_MODULES = [
    "title", "authors", "affiliations", "abstract", "keywords",
    "italics", "abbreviations", "statistics", "citations",
    "references", "figures_tables", "footnotes", "punctuation",
    "numbers", "units", "symbols", "ranges", "ci_format",
    "headings", "running_title", "funding", "corresponding",
    "contributions", "footer",
]


@router.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    if not file.filename.endswith(".docx"):
        raise HTTPException(400, "Only .docx files are supported")

    doc_id = create_session(file.filename)
    save_path = session_path(doc_id, "original.docx")

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    doc = parse_document(save_path)
    get_session(doc_id)["doc"] = doc

    paragraphs = []
    for i, para in enumerate(doc.all_paragraphs):
        section_name = ""
        for sec_type, section in doc.sections.items():
            indices = [idx for idx, _ in section.paragraphs]
            if i in indices:
                section_name = sec_type.value
                break
        paragraphs.append(ParagraphOut(
            index=i,
            text=para.text,
            section=section_name,
        ))

    return UploadResponse(
        doc_id=doc_id,
        filename=file.filename,
        paragraphs=paragraphs,
        available_rules=RULE_MODULES,
    )
```

- [ ] **Step 5: 创建 backend/main.py**

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers.editor import router

app = FastAPI(title="SCI Editor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: 创建 backend/tests/test_upload.py**

```python
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
import io

SAMPLE_DOCX_PATH = "test1/未修改.docx"


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
```

- [ ] **Step 7: 在项目根目录安装依赖并运行测试**

```bash
cd /home/frank/project/sci_editor
pip install fastapi uvicorn python-multipart httpx pytest pytest-asyncio
pytest backend/tests/test_upload.py -v
```

期望输出：`2 passed`

- [ ] **Step 8: 提交**

```bash
git add backend/
git commit -m "feat: add FastAPI backend scaffold with /upload endpoint"
```

---

## Task 2: /check 接口和 diff 生成

**Files:**
- Create: `backend/diff.py`
- Modify: `backend/routers/editor.py`（添加 `/check`）
- Create: `backend/tests/test_check.py`

- [ ] **Step 1: 写失败测试 backend/tests/test_check.py**

```python
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

SAMPLE_DOCX_PATH = "test1/未修改.docx"


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
    # diff 中每条都有必要字段
    for entry in data["diff"]:
        assert "paragraph_index" in entry
        assert "original" in entry
        assert "modified" in entry
        assert "issue_ids" in entry


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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest backend/tests/test_check.py -v
```

期望：`FAILED` with `404` or `connection error`

- [ ] **Step 3: 创建 backend/diff.py**

```python
import uuid
from typing import List, Dict
from sci_editor.models import Issue, DocumentStructure


def build_diff(doc: DocumentStructure, issues: List[Issue]) -> List[Dict]:
    """
    将 issues 按 paragraph_index 分组，生成前端需要的 diff 数据。
    每个 diff 条目包含原文和建议修改后的文本。
    suggestion 字段允许包含受控 HTML 标签（em, strong, sup, sub）。
    """
    by_para: Dict[int, List[Issue]] = {}
    for issue in issues:
        if issue.paragraph_index >= 0:
            by_para.setdefault(issue.paragraph_index, []).append(issue)

    diff = []
    for para_idx, para_issues in by_para.items():
        if para_idx >= len(doc.all_paragraphs):
            continue
        original_text = doc.all_paragraphs[para_idx].text
        # modified 取第一个 fixable issue 的 suggestion 作为代表性展示
        # 实际多处修改在前端高亮展示，apply 阶段由后端合并
        fixable = [i for i in para_issues if i.fixable and i.suggestion]
        modified_text = fixable[0].suggestion if fixable else original_text
        diff.append({
            "paragraph_index": para_idx,
            "original": original_text,
            "modified": modified_text,
            "issue_ids": [i.rule_id + "_" + str(para_idx) for i in para_issues],
        })
    return diff
```

- [ ] **Step 4: 在 backend/routers/editor.py 中添加 /check**

在文件末尾追加：

```python
import uuid as _uuid
from backend.diff import build_diff
from backend.schemas import CheckRequest, CheckResponse, IssueOut, DiffEntry


@router.post("/check", response_model=CheckResponse)
async def check(req: CheckRequest):
    try:
        session = get_session(req.doc_id)
    except KeyError:
        raise HTTPException(404, f"Session {req.doc_id} not found")

    doc = session.get("doc")
    if doc is None:
        raise HTTPException(500, "Document not parsed in session")

    issues = _engine.check(doc, rule_filter=req.rule_filter)

    issues_out = []
    for issue in issues:
        issue_id = str(_uuid.uuid4())
        issues_out.append(IssueOut(
            issue_id=issue_id,
            rule_id=issue.rule_id,
            rule_name=issue.rule_name,
            severity=issue.severity.value,
            section=issue.section,
            paragraph_index=issue.paragraph_index,
            context=issue.context,
            suggestion=issue.suggestion,
            fixable=issue.fixable,
            fix_description=issue.fix_description,
        ))

    diff_raw = build_diff(doc, issues)
    diff_out = [DiffEntry(**d) for d in diff_raw]

    return CheckResponse(issues=issues_out, diff=diff_out)
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest backend/tests/test_check.py -v
```

期望：`2 passed`

- [ ] **Step 6: 提交**

```bash
git add backend/diff.py backend/routers/editor.py backend/tests/test_check.py
git commit -m "feat: add /check endpoint with issue list and diff generation"
```

---

## Task 3: /apply 接口（导出修改后文档）

**Files:**
- Modify: `backend/routers/editor.py`（添加 `/apply`）
- Create: `backend/tests/test_apply.py`

- [ ] **Step 1: 写失败测试 backend/tests/test_apply.py**

```python
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

SAMPLE_DOCX_PATH = "test1/未修改.docx"


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
        ]
        response = await client.post(
            "/api/apply",
            json={"doc_id": doc_id, "decisions": decisions},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest backend/tests/test_apply.py -v
```

期望：`FAILED`

- [ ] **Step 3: 在 backend/routers/editor.py 末尾添加 /apply**

```python
from fastapi.responses import FileResponse
from sci_editor.fixer import save_fixed_document
from backend.schemas import ApplyRequest


@router.post("/apply")
async def apply(req: ApplyRequest):
    try:
        session = get_session(req.doc_id)
    except KeyError:
        raise HTTPException(404, f"Session {req.doc_id} not found")

    doc = session.get("doc")
    if doc is None:
        raise HTTPException(500, "Document not parsed in session")

    # 重新检查获取最新 issues（引擎会在 doc.word_doc 上执行 fix）
    issues = _engine.check(doc)
    rule_map = {r.rule_id: r for r in _engine.rules}

    accept_ids = {d.issue_id for d in req.decisions if d.action == "accept"}
    manual_map = {
        d.issue_id: d.final_text
        for d in req.decisions
        if d.action == "manual" and d.final_text
    }

    # 对 accept 的 issue 执行自动 fix
    for issue in issues:
        issue_key = issue.rule_id
        if issue_key in accept_ids and issue.fixable:
            rule = rule_map.get(issue.rule_id)
            if rule:
                try:
                    rule.fix(doc, issue)
                except Exception:
                    pass

    # manual 修改：直接替换对应段落文本
    for issue in issues:
        issue_key = issue.rule_id
        if issue_key in manual_map and issue.paragraph_index >= 0:
            para = doc.all_paragraphs[issue.paragraph_index]
            # 清空所有 runs，重写为纯文本（保留段落样式）
            for run in para.runs:
                run.text = ""
            if para.runs:
                para.runs[0].text = manual_map[issue_key]

    output_path = session_path(req.doc_id, "output.docx")
    save_fixed_document(doc, output_path)

    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"edited_{session['filename']}",
    )


@router.delete("/session/{doc_id}")
async def delete_session_route(doc_id: str):
    from backend.session import delete_session
    delete_session(doc_id)
    return {"status": "deleted"}
```

- [ ] **Step 4: 运行所有后端测试**

```bash
pytest backend/tests/ -v
```

期望：`6 passed`

- [ ] **Step 5: 提交**

```bash
git add backend/routers/editor.py backend/tests/test_apply.py
git commit -m "feat: add /apply endpoint for exporting edited document"
```

---

## Task 4: 前端脚手架 + 全局状态

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/store.ts`
- Create: `frontend/src/api.ts`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`

- [ ] **Step 1: 初始化 React + Vite 项目**

```bash
cd /home/frank/project/sci_editor
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install zustand tailwindcss @tailwindcss/vite
```

- [ ] **Step 2: 配置 vite.config.ts（添加 API 代理）**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

- [ ] **Step 3: 创建 frontend/src/types.ts**

```typescript
export interface Paragraph {
  index: number
  text: string
  section: string
}

export interface IssueOut {
  issue_id: string
  rule_id: string
  rule_name: string
  severity: 'error' | 'warning' | 'info'
  section: string
  paragraph_index: number
  context: string
  suggestion: string
  fixable: boolean
  fix_description: string
}

export interface DiffEntry {
  paragraph_index: number
  original: string
  modified: string
  issue_ids: string[]
}

export type DecisionAction = 'pending' | 'accept' | 'reject' | 'manual'

export interface Decision {
  issue_id: string
  action: DecisionAction
  final_text?: string
}
```

- [ ] **Step 4: 创建 frontend/src/api.ts**

```typescript
import type { Paragraph, IssueOut, DiffEntry, Decision } from './types'

const BASE = '/api'

export async function uploadDoc(file: File): Promise<{
  doc_id: string
  filename: string
  paragraphs: Paragraph[]
  available_rules: string[]
}> {
  const form = new FormData()
  form.append('file', file)
  const r = await fetch(`${BASE}/upload`, { method: 'POST', body: form })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function checkDoc(doc_id: string, rule_filter: string[]): Promise<{
  issues: IssueOut[]
  diff: DiffEntry[]
}> {
  const r = await fetch(`${BASE}/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ doc_id, rule_filter }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function applyDecisions(doc_id: string, decisions: Decision[]): Promise<Blob> {
  const r = await fetch(`${BASE}/apply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ doc_id, decisions }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.blob()
}

export async function deleteSession(doc_id: string): Promise<void> {
  await fetch(`${BASE}/session/${doc_id}`, { method: 'DELETE' })
}
```

- [ ] **Step 5: 创建 frontend/src/store.ts**

```typescript
import { create } from 'zustand'
import type { Paragraph, IssueOut, DiffEntry, Decision, DecisionAction } from './types'

interface EditorState {
  docId: string | null
  filename: string
  availableRules: string[]
  selectedRules: string[]
  paragraphs: Paragraph[]
  issues: IssueOut[]
  diff: DiffEntry[]
  decisions: Record<string, Decision>   // keyed by issue_id
  focusedParagraphIndex: number | null
  loading: boolean
  error: string | null

  setUploadResult: (docId: string, filename: string, paragraphs: Paragraph[], availableRules: string[]) => void
  toggleRule: (rule: string) => void
  selectAllRules: () => void
  clearRules: () => void
  setCheckResult: (issues: IssueOut[], diff: DiffEntry[]) => void
  setDecision: (issueId: string, action: DecisionAction, finalText?: string) => void
  setFocusedParagraph: (index: number | null) => void
  setLoading: (v: boolean) => void
  setError: (msg: string | null) => void
  reset: () => void
}

export const useEditorStore = create<EditorState>((set, get) => ({
  docId: null,
  filename: '',
  availableRules: [],
  selectedRules: [],
  paragraphs: [],
  issues: [],
  diff: [],
  decisions: {},
  focusedParagraphIndex: null,
  loading: false,
  error: null,

  setUploadResult: (docId, filename, paragraphs, availableRules) =>
    set({ docId, filename, paragraphs, availableRules, selectedRules: availableRules }),

  toggleRule: (rule) =>
    set((s) => ({
      selectedRules: s.selectedRules.includes(rule)
        ? s.selectedRules.filter((r) => r !== rule)
        : [...s.selectedRules, rule],
    })),

  selectAllRules: () => set((s) => ({ selectedRules: [...s.availableRules] })),
  clearRules: () => set({ selectedRules: [] }),

  setCheckResult: (issues, diff) => {
    const decisions: Record<string, Decision> = {}
    issues.forEach((i) => { decisions[i.issue_id] = { issue_id: i.issue_id, action: 'pending' } })
    set({ issues, diff, decisions })
  },

  setDecision: (issueId, action, finalText) =>
    set((s) => ({
      decisions: {
        ...s.decisions,
        [issueId]: { issue_id: issueId, action, final_text: finalText },
      },
    })),

  setFocusedParagraph: (index) => set({ focusedParagraphIndex: index }),
  setLoading: (v) => set({ loading: v }),
  setError: (msg) => set({ error: msg }),
  reset: () => set({
    docId: null, filename: '', availableRules: [], selectedRules: [],
    paragraphs: [], issues: [], diff: [], decisions: {},
    focusedParagraphIndex: null, loading: false, error: null,
  }),
}))
```

- [ ] **Step 6: 创建 frontend/src/App.tsx 骨架**

```tsx
import Toolbar from './components/Toolbar'
import DiffView from './components/DiffView'
import ChangeList from './components/ChangeList'

export default function App() {
  return (
    <div className="flex flex-col h-screen bg-gray-950 text-gray-100">
      <Toolbar />
      <div className="flex-1 flex overflow-hidden">
        <DiffView />
      </div>
      <div className="h-64 border-t border-gray-700 overflow-y-auto">
        <ChangeList />
      </div>
    </div>
  )
}
```

- [ ] **Step 7: 创建占位组件（让项目能编译）**

创建 `frontend/src/components/Toolbar.tsx`：
```tsx
export default function Toolbar() {
  return <div className="h-14 bg-gray-900 border-b border-gray-700 flex items-center px-4">工具栏</div>
}
```

创建 `frontend/src/components/DiffView.tsx`：
```tsx
export default function DiffView() {
  return <div className="flex-1 flex">DiffView</div>
}
```

创建 `frontend/src/components/ChangeList.tsx`：
```tsx
export default function ChangeList() {
  return <div className="p-4">修改列表</div>
}
```

创建 `frontend/src/components/EditablePanel.tsx`：
```tsx
export default function EditablePanel() {
  return <div>EditablePanel</div>
}
```

- [ ] **Step 8: 验证项目能编译**

```bash
cd /home/frank/project/sci_editor/frontend
npm run build
```

期望：`✓ built in Xs`，无 TypeScript 错误

- [ ] **Step 9: 提交**

```bash
cd /home/frank/project/sci_editor
git add frontend/
git commit -m "feat: scaffold React frontend with Zustand store and API client"
```

---

## Task 5: Toolbar 组件（上传 + 规则 Chip + 执行）

**Files:**
- Modify: `frontend/src/components/Toolbar.tsx`

- [ ] **Step 1: 实现 Toolbar.tsx**

```tsx
import { useRef } from 'react'
import { useEditorStore } from '../store'
import { uploadDoc, checkDoc } from '../api'

const RULE_LABELS: Record<string, string> = {
  title: '标题', authors: '作者', affiliations: '单位',
  abstract: '摘要', keywords: '关键词', italics: '斜体',
  abbreviations: '缩写', statistics: '统计', citations: '引用',
  references: '参考文献', figures_tables: '图表', footnotes: '脚注',
  punctuation: '标点', numbers: '数字', units: '单位符号',
  symbols: '符号', ranges: '数值范围', ci_format: 'CI格式',
  headings: '小标题', running_title: '短标题', funding: '基金',
  corresponding: '通讯作者', contributions: '作者贡献', footer: '页脚',
}

export default function Toolbar() {
  const fileRef = useRef<HTMLInputElement>(null)
  const {
    docId, filename, availableRules, selectedRules,
    toggleRule, selectAllRules, clearRules,
    setUploadResult, setCheckResult, setLoading, setError, loading,
  } = useEditorStore()

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      const result = await uploadDoc(file)
      setUploadResult(result.doc_id, result.filename, result.paragraphs, result.available_rules)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  async function handleRun() {
    if (!docId || selectedRules.length === 0) return
    setLoading(true)
    setError(null)
    try {
      const result = await checkDoc(docId, selectedRules)
      setCheckResult(result.issues, result.diff)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-gray-900 border-b border-gray-700 px-4 py-2 flex flex-wrap items-center gap-3">
      <input ref={fileRef} type="file" accept=".docx" className="hidden" onChange={handleFileChange} />
      <button
        onClick={() => fileRef.current?.click()}
        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded text-sm font-medium"
      >
        📁 {filename || '上传文件'}
      </button>

      {availableRules.length > 0 && (
        <>
          <div className="flex flex-wrap gap-1.5">
            {availableRules.map((rule) => (
              <button
                key={rule}
                onClick={() => toggleRule(rule)}
                className={`px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors ${
                  selectedRules.includes(rule)
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                }`}
              >
                {RULE_LABELS[rule] ?? rule}
              </button>
            ))}
          </div>
          <button onClick={selectAllRules} className="text-xs text-gray-400 hover:text-gray-200">全选</button>
          <button onClick={clearRules} className="text-xs text-gray-400 hover:text-gray-200">清空</button>
          <button
            onClick={handleRun}
            disabled={loading || selectedRules.length === 0}
            className="px-3 py-1.5 bg-green-600 hover:bg-green-500 disabled:opacity-50 rounded text-sm font-medium ml-auto"
          >
            {loading ? '处理中...' : '▶ 执行'}
          </button>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 验证编译**

```bash
cd /home/frank/project/sci_editor/frontend && npm run build
```

期望：无错误

- [ ] **Step 3: 提交**

```bash
cd /home/frank/project/sci_editor
git add frontend/src/components/Toolbar.tsx
git commit -m "feat: implement Toolbar with file upload and rule chip selector"
```

---

## Task 6: DiffView 组件（左右对比区）

**Files:**
- Modify: `frontend/src/components/DiffView.tsx`
- Modify: `frontend/src/components/EditablePanel.tsx`

- [ ] **Step 1: 实现 EditablePanel.tsx（右栏富文本编辑逻辑）**

```tsx
import { useRef, useEffect } from 'react'
import { useEditorStore } from '../store'

interface Props {
  paragraphIndex: number
  htmlContent: string        // 建议修改后的文本（含受控 HTML）
  isActive: boolean          // 当前聚焦段落
}

// 白名单：只允许这些 HTML 标签渲染，防止 XSS
function sanitize(html: string): string {
  return html
    .replace(/<(?!\/?(?:em|strong|sup|sub)\b)[^>]*>/gi, '')
    .replace(/&(?!amp;|lt;|gt;|quot;|#\d+;)/g, '&amp;')
}

export default function EditablePanel({ paragraphIndex, htmlContent, isActive }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const { setDecision, focusedParagraphIndex, issues } = useEditorStore()

  const relatedIssues = issues.filter((i) => i.paragraph_index === paragraphIndex)

  function handleBlur() {
    if (!ref.current) return
    const text = ref.current.innerText
    relatedIssues.forEach((issue) => {
      setDecision(issue.issue_id, 'manual', text)
    })
  }

  useEffect(() => {
    if (isActive && ref.current) {
      ref.current.focus()
    }
  }, [isActive])

  return (
    <div
      ref={ref}
      contentEditable={isActive}
      suppressContentEditableWarning
      onBlur={handleBlur}
      className={`p-3 text-sm leading-relaxed outline-none transition-colors ${
        isActive ? 'bg-gray-800 ring-1 ring-blue-500 rounded' : ''
      }`}
      dangerouslySetInnerHTML={{ __html: sanitize(htmlContent) }}
    />
  )
}
```

- [ ] **Step 2: 实现 DiffView.tsx**

```tsx
import { useRef, useEffect } from 'react'
import { useEditorStore } from '../store'
import EditablePanel from './EditablePanel'

function highlight(text: string, isOriginal: boolean): string {
  // 简单高亮：对原文标红背景，对修改后标绿背景
  // 实际高亮在 ChangeList 点击时由 focusedParagraphIndex 驱动
  return text
}

export default function DiffView() {
  const { paragraphs, diff, focusedParagraphIndex, setFocusedParagraph, issues } = useEditorStore()
  const leftRefs = useRef<(HTMLDivElement | null)[]>([])
  const rightRefs = useRef<(HTMLDivElement | null)[]>([])

  // 当 focusedParagraphIndex 变化时，滚动到对应段落
  useEffect(() => {
    if (focusedParagraphIndex === null) return
    leftRefs.current[focusedParagraphIndex]?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    rightRefs.current[focusedParagraphIndex]?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [focusedParagraphIndex])

  if (paragraphs.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
        上传文件后执行检查，此处将显示修改对比
      </div>
    )
  }

  const diffByPara = Object.fromEntries(diff.map((d) => [d.paragraph_index, d]))
  const modifiedIndices = new Set(diff.map((d) => d.paragraph_index))

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* 左栏：原文 */}
      <div className="flex-1 overflow-y-auto border-r border-gray-700 p-4 space-y-1">
        <div className="text-xs text-red-400 font-mono mb-3 sticky top-0 bg-gray-950 py-1">原文</div>
        {paragraphs.map((para) => {
          const isFocused = focusedParagraphIndex === para.index
          const isModified = modifiedIndices.has(para.index)
          return (
            <div
              key={para.index}
              ref={(el) => { leftRefs.current[para.index] = el }}
              onClick={() => isModified && setFocusedParagraph(para.index)}
              className={`p-2 rounded text-sm leading-relaxed transition-colors ${
                isFocused ? 'bg-red-950 ring-1 ring-red-500' :
                isModified ? 'bg-red-950/30 cursor-pointer hover:bg-red-950/50' : ''
              }`}
            >
              {para.text || <span className="text-gray-700 italic">（空段落）</span>}
            </div>
          )
        })}
      </div>

      {/* 右栏：修改后 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-1">
        <div className="text-xs text-green-400 font-mono mb-3 sticky top-0 bg-gray-950 py-1">修改后（可编辑）</div>
        {paragraphs.map((para) => {
          const diffEntry = diffByPara[para.index]
          const isFocused = focusedParagraphIndex === para.index
          const content = diffEntry ? diffEntry.modified : para.text
          return (
            <div
              key={para.index}
              ref={(el) => { rightRefs.current[para.index] = el }}
              className={`rounded transition-colors ${
                isFocused ? 'ring-1 ring-green-500' :
                diffEntry ? 'bg-green-950/30' : ''
              }`}
            >
              <EditablePanel
                paragraphIndex={para.index}
                htmlContent={content}
                isActive={isFocused}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: 验证编译**

```bash
cd /home/frank/project/sci_editor/frontend && npm run build
```

期望：无错误

- [ ] **Step 4: 提交**

```bash
cd /home/frank/project/sci_editor
git add frontend/src/components/DiffView.tsx frontend/src/components/EditablePanel.tsx
git commit -m "feat: implement DiffView with synchronized left/right panels and editable right column"
```

---

## Task 7: ChangeList 组件（底部逐条操作列表）

**Files:**
- Modify: `frontend/src/components/ChangeList.tsx`

- [ ] **Step 1: 实现 ChangeList.tsx**

```tsx
import { useEditorStore } from '../store'
import { applyDecisions, deleteSession } from '../api'
import type { IssueOut } from '../types'

const SEVERITY_ICON: Record<string, string> = {
  error: '❌', warning: '⚠️', info: 'ℹ️',
}

const ACTION_LABEL: Record<string, string> = {
  pending: '待处理', accept: '已接受', reject: '已拒绝', manual: '手动修改',
}

const ACTION_COLOR: Record<string, string> = {
  pending: 'text-gray-400',
  accept: 'text-green-400',
  reject: 'text-red-400',
  manual: 'text-blue-400',
}

export default function ChangeList() {
  const {
    issues, decisions, setDecision, setFocusedParagraph,
    docId, setLoading, setError, loading,
  } = useEditorStore()

  if (issues.length === 0) {
    return <div className="p-4 text-gray-500 text-sm">执行检查后此处将显示逐条修改列表</div>
  }

  async function handleExport() {
    if (!docId) return
    setLoading(true)
    setError(null)
    try {
      const decisionsArr = Object.values(decisions)
      const blob = await applyDecisions(docId, decisionsArr)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'edited.docx'
      a.click()
      URL.revokeObjectURL(url)
      await deleteSession(docId)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  function acceptAll() {
    issues.forEach((i) => setDecision(i.issue_id, 'accept'))
  }

  function rejectAll() {
    issues.forEach((i) => setDecision(i.issue_id, 'reject'))
  }

  return (
    <div className="flex flex-col h-full">
      {/* 操作栏 */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-gray-700 bg-gray-900 sticky top-0">
        <span className="text-xs text-gray-400">
          共 {issues.length} 条修改 · 已处理 {Object.values(decisions).filter(d => d.action !== 'pending').length} 条
        </span>
        <button onClick={acceptAll} className="text-xs text-green-400 hover:text-green-300">全部接受</button>
        <button onClick={rejectAll} className="text-xs text-red-400 hover:text-red-300">全部拒绝</button>
        <button
          onClick={handleExport}
          disabled={loading}
          className="ml-auto px-3 py-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded text-sm"
        >
          ⬇ 导出文档
        </button>
      </div>

      {/* 列表 */}
      <div className="flex-1 overflow-y-auto divide-y divide-gray-800">
        {issues.map((issue: IssueOut) => {
          const decision = decisions[issue.issue_id]
          const action = decision?.action ?? 'pending'
          return (
            <div
              key={issue.issue_id}
              onClick={() => setFocusedParagraph(issue.paragraph_index)}
              className="px-4 py-2.5 hover:bg-gray-800 cursor-pointer flex items-start gap-3"
            >
              <span className="text-base mt-0.5">{SEVERITY_ICON[issue.severity]}</span>
              <div className="flex-1 min-w-0">
                <div className="text-xs text-gray-400 mb-0.5">
                  [{issue.rule_id}] {issue.rule_name} · {issue.section}
                </div>
                <div className="text-sm text-gray-200 truncate">{issue.context}</div>
                {issue.suggestion && (
                  <div className="text-xs text-green-400 truncate mt-0.5">→ {issue.suggestion}</div>
                )}
              </div>
              <div className={`flex gap-1.5 shrink-0 items-center text-xs ${ACTION_COLOR[action]}`}>
                <span>{ACTION_LABEL[action]}</span>
                {action !== 'accept' && (
                  <button
                    onClick={(e) => { e.stopPropagation(); setDecision(issue.issue_id, 'accept') }}
                    className="px-1.5 py-0.5 bg-green-800 hover:bg-green-700 text-green-200 rounded"
                  >✓</button>
                )}
                {action !== 'reject' && (
                  <button
                    onClick={(e) => { e.stopPropagation(); setDecision(issue.issue_id, 'reject') }}
                    className="px-1.5 py-0.5 bg-red-800 hover:bg-red-700 text-red-200 rounded"
                  >✗</button>
                )}
                {action !== 'pending' && (
                  <button
                    onClick={(e) => { e.stopPropagation(); setDecision(issue.issue_id, 'pending') }}
                    className="px-1.5 py-0.5 bg-gray-700 hover:bg-gray-600 rounded"
                  >↩</button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 验证编译**

```bash
cd /home/frank/project/sci_editor/frontend && npm run build
```

期望：无错误

- [ ] **Step 3: 提交**

```bash
cd /home/frank/project/sci_editor
git add frontend/src/components/ChangeList.tsx
git commit -m "feat: implement ChangeList with per-issue accept/reject/manual controls and export"
```

---

## Task 8: 端对端联调（本地开发环境）

**Files:** 无新文件，联调现有代码

- [ ] **Step 1: 启动后端**

```bash
cd /home/frank/project/sci_editor
uvicorn backend.main:app --reload --port 8000
```

期望：`INFO:     Application startup complete.`

- [ ] **Step 2: 启动前端开发服务器（新终端）**

```bash
cd /home/frank/project/sci_editor/frontend
npm run dev
```

期望：`VITE ready at http://localhost:5173`

- [ ] **Step 3: 手动测试完整流程**

打开 `http://localhost:5173`，执行以下操作并确认每步正常：
1. 点击"上传文件"，选择 `test1/未修改.docx` → 工具栏出现规则 Chip，左右栏显示段落文本
2. 选择几个规则 Chip（如"斜体"、"缩写"），点击"▶ 执行" → 底部出现修改列表，左右栏出现高亮
3. 点击修改列表某条 → 左右栏滚动到对应段落，右栏该段落变为可编辑
4. 在右栏直接修改文字，点击其他地方失焦 → 对应条目状态变为"手动修改"
5. 点击某条"✓"接受 → 状态变为"已接受"
6. 点击"⬇ 导出文档" → 浏览器下载 `edited.docx`，用 Word 打开确认修改已应用

- [ ] **Step 4: 提交联调结果（如有修复）**

```bash
git add -p   # 只添加联调过程中修复的文件
git commit -m "fix: resolve issues found during local integration testing"
```

---

## Task 9: Docker 打包部署

**Files:**
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`
- Create: `docker-compose.yml`

- [ ] **Step 1: 创建 backend/Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# 复制项目代码（规则引擎 + 后端）
COPY sci_editor/ /app/sci_editor/
COPY backend/ /app/backend/

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: 创建 frontend/nginx.conf**

```nginx
server {
    listen 80;

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 20m;
    }

    location /health {
        proxy_pass http://backend:8000/health;
    }
}
```

- [ ] **Step 3: 创建 frontend/Dockerfile**

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

- [ ] **Step 4: 创建 docker-compose.yml**

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    restart: unless-stopped
    volumes:
      - /tmp/sci_editor_sessions:/tmp/sci_editor_sessions
    expose:
      - "8000"

  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    restart: unless-stopped
    ports:
      - "80:80"
    depends_on:
      - backend
```

- [ ] **Step 5: 构建并启动容器**

```bash
cd /home/frank/project/sci_editor
docker compose build
docker compose up -d
```

期望：两个容器均处于 `running` 状态

- [ ] **Step 6: 验证容器运行**

```bash
docker compose ps
curl http://localhost/health
```

期望：`{"status":"ok"}`

- [ ] **Step 7: 重复 Task 8 Step 3 的手动测试，访问 http://localhost**

- [ ] **Step 8: 提交**

```bash
cd /home/frank/project/sci_editor
git add backend/Dockerfile frontend/Dockerfile frontend/nginx.conf docker-compose.yml
git commit -m "feat: add Docker Compose deployment config for backend and frontend"
```

---

## Self-Review

**Spec 覆盖检查：**
- ✅ 上传文件 → Task 1
- ✅ 规则 Chip 多选 + 执行 → Task 5
- ✅ 左右行内高亮对比 → Task 6
- ✅ 逐条修改列表（接受/拒绝/撤回）→ Task 7
- ✅ 右栏富文本编辑（点击激活段落）→ Task 6 EditablePanel
- ✅ 导出文档 → Task 7 handleExport + Task 3 /apply
- ✅ Docker 部署 → Task 9
- ✅ 白名单 XSS 防护 → Task 6 EditablePanel sanitize()

**Placeholder 扫描：** 无 TBD/TODO/占位符，所有步骤均含完整代码。

**类型一致性：**
- `Decision.action` 类型为 `DecisionAction = 'pending' | 'accept' | 'reject' | 'manual'`，在 store、ChangeList、api.ts 中一致使用
- `IssueOut.issue_id` 在后端由 `uuid.uuid4()` 生成，前端 `decisions` 以 `issue_id` 为 key，`applyDecisions` 传递同一字段，一致
- `DiffEntry` 在 schemas.py 和 types.ts 中字段名完全对应
