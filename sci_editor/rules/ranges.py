"""3.15 范围与百分比规则"""

import re
from typing import List
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure
from ..utils import regex_replace_in_paragraph


class PercentageRange(BaseRule):
    rule_id = "3.15.1"
    rule_name = "百分比范围"
    section_name = "3.15 范围与百分比"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        """15%-35% 两个百分号都要有"""
        body_text = doc.get_section_text(SectionType.BODY)
        if not body_text:
            return []
        issues = []
        # 检测缺少第一个%的情况：15-35%
        matches = re.findall(r"\b(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*%", body_text)
        for num1, num2 in matches:
            # 从原文中获取上下文
            pattern = re.escape(num1) + r"\s*-\s*" + re.escape(num2) + r"\s*%"
            m = re.search(pattern, body_text)
            if m:
                context = m.group()
                # 如果第一个数字后没有%
                if "%" not in context.split("-")[0]:
                    issues.append(Issue(
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        severity=Severity.ERROR,
                        message=f"百分比范围 '{context}' 中每个数字都应带 %",
                        section=self.section_name,
                        context=context,
                        fixable=True,
                        suggestion=f"改为 {num1}%-{num2}%",
                    ))
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]

        # The pattern to find is the context of the issue, e.g., "15-35%"
        # The replacement should add the missing '%' to the first number, e.g., "15%-35%"
        # We need to capture the two numbers and the final '%'
        # The issue.context is already in the format "num1-num2%"
        # We need to ensure the pattern matches exactly what was found in the check method.
        # The check method identifies `num1-num2%` where `num1` does not have a `%`.
        # So the pattern should be `(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*%`
        # And the replacement should be `\1%-\2%`

        # Escape the context to ensure special characters are handled if present,
        # but we need to re-introduce capture groups for the numbers.
        # A more robust way is to reconstruct the pattern based on the issue's context
        # and the original regex used in check.
        # The issue.context is like "15-35%" or "1.2-3.4%"
        m_context = re.match(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*%", issue.context)
        if not m_context:
            return False # Should not happen if check method works correctly

        num1_str = re.escape(m_context.group(1))
        num2_str = re.escape(m_context.group(2))

        # Construct a precise regex pattern to find and replace the specific context
        # This pattern ensures we only replace the exact match that caused the issue.
        # We need to capture the numbers to re-insert them with the '%'
        pattern_to_fix = re.compile(rf"({num1_str})\s*-\s*({num2_str})\s*%")

        # The replacement string adds '%' after the first captured number
        replacement_string = r"\1%-\2%"

        if regex_replace_in_paragraph(para, pattern_to_fix, replacement_string):
            issue.fix_description = f"已修改为 {m_context.group(1)}%-{m_context.group(2)}%"
            return True
        return False


class CIFormat(BaseRule):
    rule_id = "3.15.2"
    rule_name = "置信区间格式"
    section_name = "3.15 范围与百分比"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        """95%CI 格式检查：含负数用 'to' 连接"""
        body_text = doc.get_section_text(SectionType.BODY)
        if not body_text:
            return []
        issues = []
        # 检查 95%CI: -0.5-0.2 格式（负数范围应用 "to"）
        matches = re.findall(r"95%\s*CI\s*[:：]\s*(-?\d+\.?\d*)\s*-\s*(-?\d+\.?\d*)", body_text)
        for low, high in matches:
            if float(low) < 0 or float(high) < 0:
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.ERROR,
                    message=f"含负数的置信区间应使用 'to' 连接（95%CI: {low} to {high}）",
                    section=self.section_name,
                    suggestion=f"改为 95%CI: {low} to {high}",
                ))
        return issues
