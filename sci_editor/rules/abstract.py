"""规则 3.9 — 摘要结构检查（依据稿件类型）"""

import re
from ..models import Issue, Severity, SectionType, DocumentStructure
from ..engine import BaseRule


# 稿件分类逻辑
REVIEW_TYPES = ["MINIREVIEWS", "REVIEW", "EDITORIAL", "LETTER TO THE EDITOR"]
CASE_REPORT_TYPE = "CASE REPORT"

# 原创类必须包含的摘要标题
ORIGINAL_SECTIONS = ["BACKGROUND", "AIM", "METHODS", "RESULTS", "CONCLUSION"]
# 病例报告摘要标题
CASE_SECTIONS = ["BACKGROUND", "CASE SUMMARY", "CONCLUSION"]


class AbstractStructureRule(BaseRule):
    rule_id = "3.9"
    rule_name = "摘要结构"
    section_name = "3.9 摘要"

    def check(self, doc: DocumentStructure):
        issues = []
        abstract_sec = doc.get_section(SectionType.ABSTRACT)
        if not abstract_sec:
            return issues

        mt = (doc.manuscript_type or "").upper()
        abs_text = abstract_sec.raw_text.upper()
        
        # 1. 综述类 (Review-style)
        if any(kw in mt for kw in REVIEW_TYPES):
            # 综述类特征：应为整段式摘要，不应含结构标题，通常为一个大段
            if len(abstract_sec.paragraphs) > 1:
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.WARNING,
                    message="综述类文章摘要通常应为整段式（单一自然段），检测到分段，请核实",
                    section=self.section_name,
                    context=abstract_sec.raw_text[:120],
                ))
            # 检查是否包含结构化关键词
            structured_headers = ORIGINAL_SECTIONS + ["CASE SUMMARY"]
            for heading in structured_headers:
                if re.search(rf"\b{heading}\b", abs_text):
                    issues.append(Issue(
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        severity=Severity.WARNING,
                        message=f"综述类文章摘要不应包含结构化标题 '{heading}'",
                        section=self.section_name,
                        context=heading,
                    ))
            return issues

        # 2. 病例报告 (Case Report)
        if CASE_REPORT_TYPE in mt:
            required = CASE_SECTIONS
        else:
            # 3. 其余判定为原创类 (Original Articles)
            required = ORIGINAL_SECTIONS

        for heading in required:
            if not re.search(rf"\b{heading}\b", abs_text):
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.WARNING,
                    message=f"摘要缺少 '{heading}' 部分",
                    section=self.section_name,
                    context=abstract_sec.raw_text[:120],
                ))

        return issues
