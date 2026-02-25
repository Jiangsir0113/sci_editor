"""3.16 数字格式规则"""

import re
from typing import List
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure


class NumberFormat(BaseRule):
    rule_id = "3.16"
    rule_name = "数字格式"
    section_name = "3.16 数字"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        issues = []
        body = doc.get_section(SectionType.BODY)
        if not body:
            return issues
            
        for idx, para in body.paragraphs:
            # 查找带逗号分隔的数字 (e.g., 10,089,600)
            matches = re.findall(r"\b(\d{1,3}(?:,\d{3})+)\b", para.text)
            for m in matches:
                # 排除参考文献引用和页码 (基本通过判断长度和后面是否有 [)
                clean = m.replace(",", "")
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.ERROR,
                    message=f"数字 '{m}' 不应使用逗号分隔",
                    section=self.section_name,
                    paragraph_index=idx,
                    context=m,
                    fixable=True,
                    suggestion=f"改为 {clean}",
                ))
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        from ..utils import regex_replace_in_paragraph
        
        # 精确匹配该数字
        pattern = re.compile(re.escape(issue.context))
        clean = issue.context.replace(",", "")
        
        if regex_replace_in_paragraph(para, pattern, clean):
            issue.fix_description = f"已去掉逗号: {clean} (已保留格式)"
            return True
        return False
