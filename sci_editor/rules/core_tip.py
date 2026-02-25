"""3.13 Core Tip 规则"""

import re
from typing import List
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure


class CoreTipWordCount(BaseRule):
    rule_id = "3.13"
    rule_name = "Core Tip 字数"
    section_name = "3.13 Core Tip"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        ct_text = doc.get_section_text(SectionType.CORE_TIP)
        if not ct_text:
            return []
        ct_text = re.sub(r"^(core\s+tip\s*[:：]\s*)", "", ct_text, flags=re.IGNORECASE).strip()
        word_count = len(ct_text.split())
        issues = []
        if word_count < 50:
            issues.append(Issue(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                severity=Severity.WARNING,
                message=f"Core Tip 字数过少（当前 {word_count} 个，要求 50-120 个）",
                section=self.section_name,
                context=ct_text[:80],
            ))
        elif word_count > 120:
            issues.append(Issue(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                severity=Severity.WARNING,
                message=f"Core Tip 字数过多（当前 {word_count} 个，要求 50-120 个）",
                section=self.section_name,
                context=ct_text[:80],
            ))
        return issues
