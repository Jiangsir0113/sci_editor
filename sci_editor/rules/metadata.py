"""规则 — 文章元信息格式检查

包含：
- Specialty type: "&" → "and", 第二个词小写
- 表格标题不应有句点
"""

import re
from ..models import Issue, Severity, SectionType, DocumentStructure
from ..engine import BaseRule


class SpecialtyTypeFormat(BaseRule):
    rule_id = "3.30.1"
    rule_name = "Specialty type 格式"
    section_name = "3.30 元信息"

    def check(self, doc: DocumentStructure):
        issues = []
        info = doc.get_section(SectionType.ARTICLE_INFO)
        if not info:
            return issues
        for idx, para in info.paragraphs:
            text = para.text.strip()
            if not text.lower().startswith("specialty type"):
                continue
            # 检查 & → and
            if " & " in text:
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.ERROR,
                    message="Specialty type 中 '&' 应替换为 'and'",
                    section=self.section_name,
                    paragraph_index=idx,
                    context=text[:80],
                    fixable=True,
                ))
            # 检查大写：Endocrinology & Metabolism → Endocrinology and metabolism
            m = re.search(r"Specialty\s+type\s*[:：]\s*(.*)", text, re.IGNORECASE)
            if m:
                specialty = m.group(1).strip()
                words = specialty.split()
                if len(words) >= 2:
                    for i, w in enumerate(words[1:], 1):
                        if w not in ("and", "of", "the", "for", "in") and w[0].isupper() and w.lower() != w:
                            issues.append(Issue(
                                rule_id=self.rule_id,
                                rule_name=self.rule_name,
                                severity=Severity.WARNING,
                                message=f"Specialty type 中 '{w}' 首字母应小写",
                                section=self.section_name,
                                paragraph_index=idx,
                                context=text[:80],
                                fixable=True,
                                suggestion=f"'{w}' → '{w[0].lower() + w[1:]}'",
                            ))
                            break
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        from ..utils import regex_replace_in_paragraph
        
        changed = False
        # 1. & → and
        if regex_replace_in_paragraph(para, re.compile(r" & "), " and "):
            changed = True
            
        # 2. 小写处理
        if "首字母应小写" in issue.message:
            m = re.search(r"首字母应小写", issue.message)
            # 我们需要一个小写替换函数来处理 specialty type 中的词
            # 这个逻辑比较复杂，因为需要跳过第一个词
            def specialty_repl(match):
                text = match.group(0)
                words = text.split()
                if not words: return text
                new_words = [words[0]]
                for w in words[1:]:
                    if w not in ("and", "of", "the", "for", "in") and w[0].isupper() and w.lower() != w:
                        new_words.append(w[0].lower() + w[1:])
                    else:
                        new_words.append(w)
                return " ".join(new_words)

            if regex_replace_in_paragraph(para, re.compile(r"(?<=Specialty type[:：]\s*).*", re.IGNORECASE), specialty_repl):
                changed = True

        if changed:
            issue.fix_description = "Specialty type 格式已修正 (已保留格式)"
        return changed


class TableTitlePeriod(BaseRule):
    rule_id = "3.30.2"
    rule_name = "表格标题句点"
    section_name = "3.30 元信息"

    PATTERN = re.compile(r"^(Table\s+\d+)\.\s+", re.IGNORECASE)

    def check(self, doc: DocumentStructure):
        issues = []
        tables = doc.get_section(SectionType.TABLES)
        if not tables:
            return issues
        for idx, para in tables.paragraphs:
            text = para.text.strip()
            # Table X. Title → Table X Title (无句点)
            m = self.PATTERN.match(text)
            if m:
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.WARNING,
                    message=f"表格标题 '{m.group(0).strip()}' 后不应有句号",
                    section=self.section_name,
                    paragraph_index=idx,
                    context=text[:60],
                    fixable=True,
                    suggestion=f"去除 '{m.group(1)}' 后的句号",
                ))
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        from ..utils import regex_replace_in_paragraph
        
        if regex_replace_in_paragraph(para, self.PATTERN, r"\1 "):
            issue.fix_description = "表格标题句号已去除 (已保留格式)"
            return True
        return False
