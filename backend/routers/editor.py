import sys
import os

# 确保能 import sci_editor（项目根目录）
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sci_editor.parser import parse_document
from sci_editor.engine import RuleEngine
from sci_editor.fixer import save_fixed_document
from backend.session import create_session, session_path, get_session, delete_session
import uuid as _uuid
from backend.schemas import UploadResponse, ParagraphOut, CheckRequest, CheckResponse, IssueOut, DiffEntry, ApplyRequest
from backend.diff import build_diff

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

    try:
        doc = parse_document(save_path)
    except Exception as exc:
        delete_session(doc_id)
        raise HTTPException(422, f"Failed to parse document: {exc}") from exc
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

    # 先为每个 issue 分配 UUID，构建带 id 的列表
    issues_with_ids = [
        {"issue_id": str(_uuid.uuid4()), "issue": issue}
        for issue in issues
    ]

    issues_out = [
        IssueOut(
            issue_id=item["issue_id"],
            rule_id=item["issue"].rule_id,
            rule_name=item["issue"].rule_name,
            severity=item["issue"].severity.value,
            section=item["issue"].section,
            paragraph_index=item["issue"].paragraph_index,
            context=item["issue"].context,
            suggestion=item["issue"].suggestion,
            fixable=item["issue"].fixable,
            fix_description=item["issue"].fix_description,
        )
        for item in issues_with_ids
    ]

    diff_raw = build_diff(doc, issues_with_ids)
    diff_out = [DiffEntry(**d) for d in diff_raw]

    # 将 issues_out 存入 session 供 /apply 使用（精确 issue_id 匹配）
    session["issues_out"] = issues_out

    return CheckResponse(issues=issues_out, diff=diff_out)


@router.post("/apply")
async def apply(req: ApplyRequest):
    try:
        session = get_session(req.doc_id)
    except KeyError:
        raise HTTPException(404, f"Session {req.doc_id} not found")

    doc = session.get("doc")
    if doc is None:
        raise HTTPException(500, "Document not parsed in session")

    # 从 session 取出上次 /check 生成的 issues（带 issue_id）
    stored_issues = session.get("issues_out", [])
    issue_map = {i.issue_id: i for i in stored_issues}

    accept_rule_ids = set()
    manual_map: dict = {}  # paragraph_index -> final_text

    for decision in req.decisions:
        if decision.action == "accept":
            issue = issue_map.get(decision.issue_id)
            if issue and issue.fixable:
                accept_rule_ids.add(issue.rule_id)
        elif decision.action == "manual" and decision.final_text is not None:
            issue = issue_map.get(decision.issue_id)
            if issue and issue.paragraph_index >= 0:
                manual_map[issue.paragraph_index] = decision.final_text

    # 重新 check 获取当前 issues（用于执行 fix）
    all_issues = _engine.check(doc)
    rule_map = {r.rule_id: r for r in _engine.rules}

    for issue in all_issues:
        if issue.rule_id in accept_rule_ids and issue.fixable:
            rule = rule_map.get(issue.rule_id)
            if rule:
                try:
                    rule.fix(doc, issue)
                except Exception:
                    pass

    # 手动修改：直接替换段落文本（保留第一个 run 的样式）
    for para_idx, final_text in manual_map.items():
        if para_idx < len(doc.all_paragraphs):
            para = doc.all_paragraphs[para_idx]
            for run in para.runs:
                run.text = ""
            if para.runs:
                para.runs[0].text = final_text

    output_path = session_path(req.doc_id, "output.docx")
    save_fixed_document(doc, output_path)

    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"edited_{session['filename']}",
    )


@router.delete("/session/{doc_id}")
async def delete_session_route(doc_id: str):
    delete_session(doc_id)
    return {"status": "deleted"}
