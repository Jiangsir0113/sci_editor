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
