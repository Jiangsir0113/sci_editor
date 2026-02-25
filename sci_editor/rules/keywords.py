"""3.11 关键词规则"""

import re
from typing import List
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure


class KeywordCount(BaseRule):
    rule_id = "3.11.2"
    rule_name = "关键词数量"
    section_name = "3.11 关键词"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        kw_text = doc.get_section_text(SectionType.KEYWORDS)
        if not kw_text:
            return []
        kw_text = re.sub(r"^(key\s*words?\s*[:：]\s*)", "", kw_text, flags=re.IGNORECASE).strip()
        keywords = [k.strip() for k in re.split(r"[;；]", kw_text) if k.strip()]
        issues = []
        if len(keywords) < 5:
            issues.append(Issue(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                severity=Severity.ERROR,
                message=f"关键词数量不足（当前 {len(keywords)} 个，要求 5-10 个）",
                section=self.section_name,
                context=kw_text[:80],
            ))
        elif len(keywords) > 10:
            issues.append(Issue(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                severity=Severity.WARNING,
                message=f"关键词数量过多（当前 {len(keywords)} 个，要求 5-10 个）",
                section=self.section_name,
            ))
        return issues


class KeywordCapitalization(BaseRule):
    rule_id = "3.11.1"
    rule_name = "关键词大写"
    section_name = "3.11 关键词"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        """关键词分号后首字母大写"""
        kw_text = doc.get_section_text(SectionType.KEYWORDS)
        if not kw_text:
            return []
        kw_text = re.sub(r"^(key\s*words?\s*[:：]\s*)", "", kw_text, flags=re.IGNORECASE).strip()
        keywords = [k.strip() for k in re.split(r"[;；]", kw_text) if k.strip()]
        issues = []
        for kw in keywords:
            if kw and kw[0].islower():
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.ERROR,
                    message=f"关键词 '{kw}' 首字母应大写",
                    section=self.section_name,
                    context=kw,
                    fixable=True,
                    suggestion=f"改为 '{kw[0].upper() + kw[1:]}'",
                ))
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        section = doc.get_section(SectionType.KEYWORDS)
        if not section:
            return False
        for _, para in section.paragraphs:
            for run in para.runs:
                kws = re.split(r"([;；])", run.text)
                new_parts = []
                changed = False
                for part in kws:
                    stripped = part.lstrip()
                    if stripped and stripped[0].islower() and part not in (";", "；"):
                        leading = part[:len(part) - len(stripped)]
                        part = leading + stripped[0].upper() + stripped[1:]
                        changed = True
                    new_parts.append(part)
                if changed:
                    run.text = "".join(new_parts)
                    issue.fix_description = "关键词首字母已大写"
                    return True
        return False


class KeywordCaseReport(BaseRule):
    rule_id = "3.11.3"
    rule_name = "关键词含Case report"
    section_name = "3.11 关键词"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        """Case report类型文章的关键词应包含 Case report"""
        title_text = doc.get_section_text(SectionType.TITLE).lower()
        if "case report" not in title_text:
            return []
        kw_text = doc.get_section_text(SectionType.KEYWORDS).lower()
        if "case report" not in kw_text:
            return [Issue(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                severity=Severity.WARNING,
                message="Case report 类型文章的关键词应包含 'Case report'",
                section=self.section_name,
            )]
        return []
