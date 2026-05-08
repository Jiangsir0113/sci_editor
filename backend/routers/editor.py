import sys
import os
import uuid as _uuid

# 确保能 import sci_editor（项目根目录）
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi import APIRouter, UploadFile, File, HTTPException
from sci_editor.parser import parse_document
from sci_editor.engine import RuleEngine
from backend.session import create_session, session_path, get_session
from backend.schemas import UploadResponse, ParagraphOut

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
