"""规则 — STROBE/CONSORT 等声明标准化

检查常见声明的措辞是否符合标准：
- STROBE Statement-checklist of items
- CONSORT
- PRISMA
"""

import re
from ..models import Issue, Severity, SectionType, DocumentStructure
from ..engine import BaseRule


# 标准措辞模板
STATEMENT_TEMPLATES = {
    "STROBE": {
        "pattern": re.compile(r"STROBE\s+Statement\s*[–-]\s*Checklist", re.IGNORECASE),
        "correct": "STROBE Statement-checklist of items",
        "full_pattern": re.compile(
            r"(STROBE\s+statement.*?)(?:\.|$)",
            re.IGNORECASE | re.DOTALL,
        ),
        "correct_full": "The authors have read the STROBE Statement-checklist of items, and the manuscript was prepared and revised according to the STROBE Statement-checklist of items.",
    },
    "CONSORT": {
        "pattern": re.compile(r"CONSORT\s+Statement\s*[–-]\s*Checklist", re.IGNORECASE),
        "correct": "CONSORT Statement-checklist of items",
    },
    "PRISMA": {
        "pattern": re.compile(r"PRISMA\s+Statement\s*[–-]\s*Checklist", re.IGNORECASE),
        "correct": "PRISMA Statement-checklist of items",
    },
}


class StatementFormat(BaseRule):
    rule_id = "3.29"
    rule_name = "声明格式"
    section_name = "3.29 声明"

    def check(self, doc: DocumentStructure):
        issues = []
        # 检查所有可能包含声明的区段
        for section_type in [SectionType.FOOTNOTES, SectionType.BODY, SectionType.ARTICLE_INFO]:
            section = doc.get_section(section_type)
            if not section:
                continue
            for idx, para in section.paragraphs:
                text = para.text
                for name, template in STATEMENT_TEMPLATES.items():
                    if template["pattern"].search(text):
                        issues.append(Issue(
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            severity=Severity.WARNING,
                            message=f"'{name} Statement' 措辞不规范",
                            section=self.section_name,
                            paragraph_index=idx,
                            context=text[:80],
                            fixable=True,
                            suggestion=f"改为 '{template['correct']}'",
                        ))

                # 额外检查 "in accordance with this checklist" 措辞
                if "in accordance with" in text.lower() and "strobe" in text.lower():
                    issues.append(Issue(
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        severity=Severity.WARNING,
                        message="STROBE 声明措辞应使用标准模板",
                        section=self.section_name,
                        paragraph_index=idx,
                        context=text[:80],
                        fixable=True,
                        suggestion="改为 '...was prepared and revised according to the STROBE Statement-checklist of items.'",
                    ))

        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        from ..utils import regex_replace_in_paragraph
        
        changed = False
        for name, template in STATEMENT_TEMPLATES.items():
            if regex_replace_in_paragraph(para, template["pattern"], template["correct"]):
                changed = True

        # "in accordance with this checklist" → "according to the STROBE Statement-checklist of items"
        pattern_in_accordance = re.compile(r"in accordance with this checklist", re.IGNORECASE)
        if regex_replace_in_paragraph(para, pattern_in_accordance, "according to the STROBE Statement-checklist of items"):
            changed = True

        if changed:
            issue.fix_description = "声明措辞已规范化 (已保留格式)"
        return changed
