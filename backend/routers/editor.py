import sys
import os

# 确保能 import sci_editor（项目根目录）
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi import APIRouter, UploadFile, File, HTTPException
from sci_editor.parser import parse_document
from sci_editor.engine import RuleEngine
from backend.session import create_session, session_path, get_session, delete_session
import uuid as _uuid
from backend.schemas import UploadResponse, ParagraphOut, CheckRequest, CheckResponse, IssueOut, DiffEntry
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

    return CheckResponse(issues=issues_out, diff=diff_out)
