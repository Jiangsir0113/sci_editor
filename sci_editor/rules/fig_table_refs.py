"""3.19-3.20 图表引用规则"""

import re
from typing import List
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure


class FigureReferenceFormat(BaseRule):
    rule_id = "3.19"
    rule_name = "图引用格式"
    section_name = "3.19 图引用"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        issues = []
        body = doc.get_section(SectionType.BODY)
        if not body:
            return issues

        for idx, para in body.paragraphs:
            text = para.text
            # 3.19.1 如果图1只有ABCD四个分图，Figure 1A-D 改为 Figure 1
            # 这里只能做格式检查，不能判断实际子图数量

            # 3.19.2 跨图片分图要加 s: Figures 1A and 2B（不是 Figure 1A and 2B)
            cross_fig = re.findall(r"\bFigure\s+(\d+[A-Z]?\s+and\s+\d+[A-Z]?)", text)
            for m in cross_fig:
                nums = re.findall(r"(\d+)", m)
                if len(nums) >= 2 and nums[0] != nums[1]:
                    issues.append(Issue(
                        rule_id="3.19.2",
                        rule_name="跨图引用加s",
                        severity=Severity.ERROR,
                        message=f"跨越不同图时应使用 'Figures'（复数）: 'Figure {m}' → 'Figures {m}'",
                        section=self.section_name,
                        paragraph_index=idx,
                        context=f"Figure {m}",
                        fixable=True,
                    ))

            # 3.19.3 同时引用3张图: Figures 1, 2, and 3
            multi_fig = re.findall(r"\bFigure\s+(\d+\s*,\s*\d+\s*,)", text)
            for m in multi_fig:
                issues.append(Issue(
                    rule_id="3.19.3",
                    rule_name="多图引用格式",
                    severity=Severity.ERROR,
                    message=f"引用3张及以上图时使用 'Figures'（复数），并用 Oxford 逗号",
                    section=self.section_name,
                    paragraph_index=idx,
                    context=f"Figure {m}...",
                    fixable=True,
                ))

            # 引用两个子图用 and: Figure 1A and B
            # 引用3个及以上子图用连字符: Figure 1A-C
            subfig_and = re.findall(r"\bFigure\s+\d+([A-Z])\s+and\s+([A-Z])\s+and\s+([A-Z])", text)
            for a, b, c in subfig_and:
                issues.append(Issue(
                    rule_id="3.19.1",
                    rule_name="子图引用连字符",
                    severity=Severity.WARNING,
                    message=f"引用3个及以上子图应使用连字符格式（如 Figure 1{a}-{c}）",
                    section=self.section_name,
                    paragraph_index=idx,
                ))

        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        from ..utils import regex_replace_in_paragraph
        
        if "复数" in issue.message:
            # 跨图引用: Figure → Figures
            pattern = re.compile(r"\bFigure\s+(\d+[A-Z]?\s+and\s+(\d+)[A-Z]?)")
            def replacer(m):
                nums = re.findall(r"(\d+)", m.group(1))
                if len(nums) >= 2 and nums[0] != nums[1]:
                    return "Figures " + m.group(1)
                return m.group()
                
            if regex_replace_in_paragraph(para, pattern, replacer):
                issue.fix_description = "已改为 Figures（复数）(已保留格式)"
                return True
        return False


class TableReferenceFormat(BaseRule):
    rule_id = "3.20"
    rule_name = "表格引用格式"
    section_name = "3.20 表格引用"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        issues = []
        body = doc.get_section(SectionType.BODY)
        if not body:
            return issues

        for idx, para in body.paragraphs:
            text = para.text
            # 多表格引用: Table 1, 2, and 3 → Tables 1, 2, and 3
            multi_tbl = re.findall(r"\bTable\s+(\d+\s*,\s*\d+)", text)
            for m in multi_tbl:
                issues.append(Issue(
                    rule_id="3.20.1",
                    rule_name="多表格引用",
                    severity=Severity.ERROR,
                    message=f"引用多个表格时应使用 'Tables'（复数）",
                    section=self.section_name,
                    paragraph_index=idx,
                    context=f"Table {m}",
                    fixable=True,
                ))

            # 补充图表: Supplementary Table/Figure
            supp = re.findall(r"\bsupplemental\s+(table|figure)", text, re.IGNORECASE)
            for s_type in supp:
                issues.append(Issue(
                    rule_id="3.20.2",
                    rule_name="补充图表用词",
                    severity=Severity.WARNING,
                    message=f"应使用 'Supplementary' 而非 'Supplemental'",
                    section=self.section_name,
                    paragraph_index=idx,
                    fixable=True,
                ))

        return issues
