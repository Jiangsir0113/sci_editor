"""规则 — 标点与大小写

包含：
- 冒号后首字母大写
- Model → model（非句首应小写）
"""

import re
from ..models import Issue, Severity, SectionType, DocumentStructure
from ..engine import BaseRule


class ColonCapitalization(BaseRule):
    rule_id = "3.31.1"
    rule_name = "冒号后大写"
    section_name = "3.31 标点"

    def check(self, doc: DocumentStructure):
        issues = []
        body = doc.get_section(SectionType.BODY)
        if not body:
            return issues
        for idx, para in body.paragraphs:
            text = para.text
            # 查找冒号后紧跟小写字母的情况
            for m in re.finditer(r":\s+([a-z])", text):
                # 排除 URL 和常见缩写
                before = text[max(0, m.start()-10):m.start()]
                if "http" in before.lower() or "doi" in before.lower():
                    continue
                # 排除 95%CI: 0.64 等数字
                if re.search(r"\d$", before):
                    continue
                lower_char = m.group(1)
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.WARNING,
                    message=f"冒号后 '{lower_char}' 首字母应大写",
                    section=self.section_name,
                    paragraph_index=idx,
                    context=text[max(0, m.start()-15):m.end()+15],
                    fixable=True,
                ))
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        from ..utils import regex_replace_in_paragraph
        
        def upper_after_colon(m):
            return m.group(0)[:-1] + m.group(1).upper()
            
        if regex_replace_in_paragraph(para, re.compile(r":\s+([a-z])"), upper_after_colon):
            issue.fix_description = "冒号后已大写 (已保留格式)"
            return True
        return False


class ModelLowercase(BaseRule):
    rule_id = "3.31.2"
    rule_name = "Model 大小写"
    section_name = "3.31 标点"

    def check(self, doc: DocumentStructure):
        issues = []
        body = doc.get_section(SectionType.BODY)
        if not body:
            return issues
        for idx, para in body.paragraphs:
            text = para.text
            # 查找非句首的 "Model" (前面有字母或标点)
            for m in re.finditer(r"(?<=[a-z.,;)\s])\s+Model\s+(\d)", text):
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.WARNING,
                    message=f"'Model {m.group(1)}' 在句中应为 'model {m.group(1)}'（非句首小写）",
                    section=self.section_name,
                    paragraph_index=idx,
                    context=text[max(0, m.start()-10):m.end()+5],
                    fixable=True,
                    suggestion=f"改为 'model {m.group(1)}'",
                ))
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        from ..utils import regex_replace_in_paragraph
        
        pattern = re.compile(r"(?<=[a-z.,;)\s])\s+Model\s+(\d)")
        def repl_fn(m):
            return m.group(0).replace("Model", "model")
            
        if regex_replace_in_paragraph(para, pattern, repl_fn):
            issue.fix_description = "'Model' → 'model' (已保留格式)"
            return True
        return False
