"""3.14 正文引用规则

- ≥3条连续引用用[4-6]格式
- 句号引用 [1.2] → [1,2]
- 相邻引用合并 [14,15][20] → [14,15,20]
- et al 后引用不应有点
"""

import re
from typing import List
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure


class CitationConsecutiveFormat(BaseRule):
    rule_id = "3.14.1"
    rule_name = "连续引用格式"
    section_name = "3.14 正文引用"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        issues = []
        body = doc.get_section(SectionType.BODY)
        if not body:
            return issues
            
        for idx, para in body.paragraphs:
            # 查找 [n,n,n] 格式的引用
            bracket_refs = re.findall(r"\[[\d,\s-]+\]", para.text)
            for ref in bracket_refs:
                inner = ref[1:-1].strip()
                nums = [int(n.strip()) for n in inner.split(",") if n.strip().isdigit()]
                if len(nums) >= 3:
                    is_consecutive = all(nums[i+1] == nums[i] + 1 for i in range(len(nums) - 1))
                    if is_consecutive:
                        issues.append(Issue(
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            severity=Severity.ERROR,
                            message=f"连续引用 {ref} 应使用连字符格式 [{nums[0]}-{nums[-1]}]",
                            section=self.section_name,
                            paragraph_index=idx,
                            context=ref,
                            fixable=True,
                            suggestion=f"改为 [{nums[0]}-{nums[-1]}]",
                        ))

                # 检查数字之间有空格
                if re.search(r"\d\s*,\s+\d", inner) or re.search(r"\d\s+-\s+\d", inner):
                    issues.append(Issue(
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        severity=Severity.ERROR,
                        message=f"引用 {ref} 中数字之间不应有空格",
                        section=self.section_name,
                        paragraph_index=idx,
                        context=ref,
                        fixable=True,
                        suggestion="去掉数字间的空格",
                    ))
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        from ..utils import regex_replace_in_paragraph
        
        if "连字符" in issue.message:
            inner = issue.context[1:-1]
            nums = [int(n.strip()) for n in inner.split(",") if n.strip().isdigit()]
            replacement = f"[{nums[0]}-{nums[-1]}]"
            if regex_replace_in_paragraph(para, re.compile(re.escape(issue.context)), replacement):
                issue.fix_description = f"已改为 {replacement} (已保留格式)"
                return True
        elif "空格" in issue.message:
            new_ref = re.sub(r"(\d)\s*,\s+(\d)", r"\1,\2", issue.context)
            new_ref = re.sub(r"(\d)\s+-\s+(\d)", r"\1-\2", new_ref)
            if regex_replace_in_paragraph(para, re.compile(re.escape(issue.context)), new_ref):
                issue.fix_description = "已去掉引用数字间的空格 (已保留格式)"
                return True
        return False


class CitationPeriodSeparator(BaseRule):
    rule_id = "3.14.3"
    rule_name = "引用句号分隔"
    section_name = "3.14 正文引用"

    # [1.2] → [1,2]
    DOT_CITATION = re.compile(r"\[(\d+)\.(\d+)\]")

    def check(self, doc: DocumentStructure) -> List[Issue]:
        issues = []
        body = doc.get_section(SectionType.BODY)
        if not body:
            return issues
            
        for idx, para in body.paragraphs:
            for m in self.DOT_CITATION.finditer(para.text):
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.ERROR,
                    message=f"引用 '{m.group()}' 中使用了句号分隔，应用逗号",
                    section=self.section_name,
                    paragraph_index=idx,
                    context=m.group(),
                    fixable=True,
                    suggestion=f"改为 [{m.group(1)},{m.group(2)}]",
                ))
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        from ..utils import regex_replace_in_paragraph
        
        def repl_fn(m):
            return f"[{m.group(1)},{m.group(2)}]"
            
        if regex_replace_in_paragraph(para, self.DOT_CITATION, repl_fn):
            issue.fix_description = "引用句号已替换为逗号 (已保留格式)"
            return True
        return False


class CitationAdjacentMerge(BaseRule):
    rule_id = "3.14.4"
    rule_name = "相邻引用合并"
    section_name = "3.14 正文引用"

    # [14,15][20] or [14][15] 等相邻引用
    ADJACENT_CITATION = re.compile(r"\[([\d,\s-]+)\]\s*\[([\d,\s-]+)\]")

    def check(self, doc: DocumentStructure) -> List[Issue]:
        issues = []
        body = doc.get_section(SectionType.BODY)
        if not body: return issues
        
        for idx, para in body.paragraphs:
            for m in self.ADJACENT_CITATION.finditer(para.text):
                merged = f"[{m.group(1).strip()},{m.group(2).strip()}]"
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.ERROR,
                    message=f"相邻引用 '{m.group()}' 应合并为 '{merged}'",
                    section=self.section_name,
                    paragraph_index=idx,
                    context=m.group(),
                    fixable=True,
                    suggestion=f"合并为 {merged}",
                ))
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        from ..utils import regex_replace_in_paragraph
        
        def repl_fn(m):
            return f"[{m.group(1).strip()},{m.group(2).strip()}]"
            
        if regex_replace_in_paragraph(para, self.ADJACENT_CITATION, repl_fn):
            issue.fix_description = "相邻引用已合并 (已保留格式)"
            return True
        return False


class CitationAuthorFormat(BaseRule):
    rule_id = "3.14.2"
    rule_name = "作者引用格式"
    section_name = "3.14 正文引用"

    PATTERN = re.compile(r"et\s+al\.\s*\[", re.IGNORECASE)

    def check(self, doc: DocumentStructure) -> List[Issue]:
        issues = []
        body = doc.get_section(SectionType.BODY)
        if not body: return issues
        
        for idx, para in body.paragraphs:
            for m in self.PATTERN.finditer(para.text):
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.ERROR,
                    message="'et al.' 后跟引用号时不应有句点，应为 'et al[n]'",
                    section=self.section_name,
                    paragraph_index=idx,
                    context=m.group(),
                    fixable=True,
                ))
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        from ..utils import regex_replace_in_paragraph
        
        if regex_replace_in_paragraph(para, self.PATTERN, "et al["):
            issue.fix_description = "'et al.' → 'et al' (已保留格式)"
            return True
        return False
