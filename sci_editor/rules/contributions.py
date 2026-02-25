"""3.5 作者贡献规则

- 职责描述，分号隔开，最后 and
- 最后需加 "All authors approved the final version to publish."
- Oxford comma ( , and )
- co-first authors / co-corresponding authors 声明
"""

import re
from typing import List
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure


class ContributionsFormat(BaseRule):
    rule_id = "3.5"
    rule_name = "作者贡献格式"
    section_name = "3.5 作者贡献"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        issues = []
        section = doc.get_section(SectionType.CONTRIBUTIONS)
        if not section:
            return []

        # 3.5.1 检查末尾批准声明
        full_text = doc.get_section_text(SectionType.CONTRIBUTIONS)
        if "approved" not in full_text.lower() or "final version" not in full_text.lower():
            # 标记在最后一段
            idx, _ = section.paragraphs[-1]
            issues.append(Issue(
                rule_id="3.5.1",
                rule_name="批准声明缺失",
                severity=Severity.ERROR,
                message="作者贡献末尾应包含：'All authors approved the final version to publish.'",
                section=self.section_name,
                paragraph_index=idx,
                fixable=True,
                suggestion="添加批准声明",
            ))

        # 3.5.2 Oxford comma 检查 ( , and )
        for idx, para in section.paragraphs:
            text = para.text
            if re.search(r"(\w+),\s+(\w+)\s+and\s+(\w+)", text):
                if not re.search(r"(\w+),\s+(\w+),\s+and\s+(\w+)", text):
                    issues.append(Issue(
                        rule_id="3.5.5",
                        rule_name="Oxford comma",
                        severity=Severity.WARNING,
                        message="建议在 'and' 前使用 Oxford comma（即 ', and'）",
                        section=self.section_name,
                        paragraph_index=idx,
                        context=text[-60:],
                        fixable=True,
                    ))

        # 3.5.3 检查 co-first/co-corresponding 声明
        for idx, para in section.paragraphs:
            text = para.text
            if "contribute" in text.lower() and "equally" in text.lower():
                if "co-first" not in text.lower() and "co-corresponding" not in text.lower():
                    issues.append(Issue(
                        rule_id="3.5.6",
                        rule_name="并列作者描述",
                        severity=Severity.INFO,
                        message="文中提到共同贡献，请核实是否列出了 'co-first authors' 或 'co-corresponding authors'",
                        section=self.section_name,
                        paragraph_index=idx,
                        context=text[:100],
                    ))

        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        from ..utils import regex_replace_in_paragraph

        if "批准声明缺失" in issue.rule_name:
            # 在该段末尾追加
            # 我们需要捕获整个段落内容并修改
            # regex_replace_in_paragraph 可以用来替换整个段落
            def repl_fn(m):
                text = m.group(0).strip()
                if not text.endswith("."):
                    text += "."
                return text + " All authors approved the final version to publish."
                
            if regex_replace_in_paragraph(para, re.compile(".*", re.DOTALL), repl_fn):
                issue.fix_description = "已添加批准声明 (已保留格式)"
                return True

        if "Oxford comma" in issue.rule_name:
            pattern = re.compile(r"(\w+),\s+(\w+)\s+and\s+(\w+)")
            replacement = r"\1, \2, and \3"
            if regex_replace_in_paragraph(para, pattern, replacement):
                issue.fix_description = "已添加 Oxford comma (已保留格式)"
                return True

        return False
