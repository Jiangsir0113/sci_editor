"""3.24 脚注规则"""

import re
from typing import List
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure


# 脚注应包含的关键内容（按顺序）
FOOTNOTE_SECTIONS = [
    "伦理声明",
    "OA",
    "手稿来源",
    "学科",
    "国家",
    "评级",
    "审稿人",
    "S-Editor",
    "L-Editor",
]

FOOTNOTE_KEYWORDS_EN = [
    "Institutional review board",
    "Ethics",
    "Open-Access",
    "Provenance",
    "Peer-review",
    "Specialty type",
    "Country",
    "S-Editor",
    "L-Editor",
]


class FootnoteCheck(BaseRule):
    rule_id = "3.24"
    rule_name = "脚注内容检查"
    section_name = "3.24 脚注"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        fn_text = doc.get_section_text(SectionType.FOOTNOTES)
        if not fn_text:
            return []
        issues = []

        # 检查关键内容是否存在
        for kw in FOOTNOTE_KEYWORDS_EN:
            if kw.lower() not in fn_text.lower():
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.INFO,
                    message=f"脚注可能缺少 '{kw}' 相关内容",
                    section=self.section_name,
                ))

        return issues
