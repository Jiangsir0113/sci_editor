"""规则 — 符号规范化

包含：
- ≧ → ≥ 替换（日式符号→标准符号）
- 上标 ² → 普通 2（后续需上标处理）
- 直引号 → 弯引号
- chi-square / chi square → χ²
- – (en dash) → - (hyphen) 在引用中
"""

import re
from ..models import Issue, Severity, SectionType, DocumentStructure
from ..engine import BaseRule


class SymbolNormalize(BaseRule):
    rule_id = "3.28.1"
    rule_name = "符号规范化"
    section_name = "3.28 符号"

    # 需要替换的符号对
    SYMBOL_MAP = {
        "≧": "≥",
        "≦": "≤",
        # en dash → hyphen (仅在特定上下文)
    }

    def check(self, doc: DocumentStructure):
        issues = []
        for section_type in [SectionType.BODY, SectionType.ABSTRACT, SectionType.TABLES]:
            section = doc.get_section(section_type)
            if not section:
                continue
            for idx, para in section.paragraphs:
                text = para.text
                for old_sym, new_sym in self.SYMBOL_MAP.items():
                    if old_sym in text:
                        issues.append(Issue(
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            severity=Severity.ERROR,
                            message=f"'{old_sym}' 应替换为 '{new_sym}'",
                            section=self.section_name,
                            paragraph_index=idx,
                            context=text[max(0, text.index(old_sym)-10):text.index(old_sym)+15],
                            fixable=True,
                            suggestion=f"替换为 '{new_sym}'",
                        ))
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        from ..utils import regex_replace_in_paragraph
        
        changed = False
        for old_sym, new_sym in self.SYMBOL_MAP.items():
            if regex_replace_in_paragraph(para, re.compile(re.escape(old_sym)), new_sym):
                changed = True
        if changed:
            issue.fix_description = "符号已替换 (已保留格式)"
        return changed


class ChiSquareFormat(BaseRule):
    rule_id = "3.28.2"
    rule_name = "卡方符号格式"
    section_name = "3.28 符号"

    # chi-square / chi square / Chi-square 等 → χ²
    CHI_PATTERN = re.compile(r"\bchi[\s-]?square\b", re.IGNORECASE)

    def check(self, doc: DocumentStructure):
        issues = []
        for section_type in [SectionType.BODY, SectionType.ABSTRACT, SectionType.TABLES]:
            section = doc.get_section(section_type)
            if not section:
                continue
            for idx, para in section.paragraphs:
                text = para.text
                for m in self.CHI_PATTERN.finditer(text):
                    issues.append(Issue(
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        severity=Severity.ERROR,
                        message=f"'{m.group()}' 应替换为 'χ²'",
                        section=self.section_name,
                        paragraph_index=idx,
                        context=text[max(0, m.start()-10):m.end()+10],
                        fixable=True,
                        suggestion="替换为 χ²",
                    ))
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        from ..utils import regex_replace_in_paragraph
        
        if regex_replace_in_paragraph(para, self.CHI_PATTERN, "χ²"):
            issue.fix_description = "chi-square 已替换为 χ² (已保留格式)"
            return True
        return False


class QuoteFormat(BaseRule):
    rule_id = "3.28.3"
    rule_name = "引号格式"
    section_name = "3.28 符号"

    def check(self, doc: DocumentStructure):
        issues = []
        body = doc.get_section(SectionType.BODY)
        if not body:
            return issues
        for idx, para in body.paragraphs:
            text = para.text
            # 检查直引号
            if '"' in text:
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.WARNING,
                    message="正文中使用了直引号 '\"'，应替换为弯引号 '\u201c...\u201d'",
                    section=self.section_name,
                    paragraph_index=idx,
                    context=text[:80],
                    fixable=True,
                ))
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        from ..utils import regex_replace_in_paragraph
        
        # 使用正则表达式配合回调函数来实现左右引号交替
        # 注意：这里我们假设引号是成对出现的，如果跨 Run 可能有挑战，
        # 但 regex_replace_in_paragraph 处理了文本层面的连续性。
        state = {"is_open": True}
        def quote_repl(m):
            res = "\u201c" if state["is_open"] else "\u201d"
            state["is_open"] = not state["is_open"]
            return res
            
        if regex_replace_in_paragraph(para, re.compile('"'), quote_repl):
            issue.fix_description = "直引号已替换为弯引号 (已保留格式)"
            return True
        return False
