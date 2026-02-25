"""3.6 基金规则

- 多个基金之间分号隔开，最后一个用 and
- 同一基金多个编号合并
- 基金名称实词首字母大写
- 去掉冗余 "This work was supported by"
- 基金编号格式 "No. xxx"（而非 "(No.xxx)"）
"""

import re
from typing import List
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure


class FundingFormat(BaseRule):
    rule_id = "3.6"
    rule_name = "基金格式"
    section_name = "3.6 基金"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        issues = []
        section = doc.get_section(SectionType.FUNDING)
        if not section:
            return []
            
        for idx, para in section.paragraphs:
            text = para.text
            # 3.6.1 多个基金之间分号隔开，最后一个用 and
            if "No." in text:
                nos = re.findall(r"No\.\s*\w+", text)
                if len(nos) > 1 and ";" not in text:
                    issues.append(Issue(
                        rule_id="3.6.1",
                        rule_name="多基金分号分隔",
                        severity=Severity.WARNING,
                        message="多个基金项之间应以分号隔开，最后一个用 'and' 连接",
                        section=self.section_name,
                        paragraph_index=idx,
                        context=text[:100],
                    ))

            # 3.6.2 同一基金多个编号合并
            foundations = re.findall(r"(National\s+\w+\s+Foundation[^;]*)", text, re.IGNORECASE)
            if len(foundations) > 1:
                issues.append(Issue(
                    rule_id="3.6.2",
                    rule_name="同基金项目合并",
                    severity=Severity.WARNING,
                    message="同一基金的多个项目编号应合并列出",
                    section=self.section_name,
                    paragraph_index=idx,
                    context=text[:100],
                    suggestion="如 'Supported by NSFC, No. 81600693 and No. 81600694.'",
                ))

            # 3.6.3 冗余 "This work was supported by" 在 "Supported by" 之后
            if re.search(r"Supported\s+by\s+This\s+work\s+was\s+supported\s+by", text, re.IGNORECASE):
                issues.append(Issue(
                    rule_id="3.6.3",
                    rule_name="基金冗余措辞",
                    severity=Severity.ERROR,
                    message="'Supported by' 后不应再有 'This work was supported by'",
                    section=self.section_name,
                    paragraph_index=idx,
                    context=text[:100],
                    fixable=True,
                    suggestion="删除冗余的 'This work was supported by'",
                ))

            # 3.6.4 基金编号格式：(No.xxx) → No. xxx
            if re.search(r"\(No\.\s*\w+\)", text):
                issues.append(Issue(
                    rule_id="3.6.4",
                    rule_name="基金编号格式",
                    severity=Severity.WARNING,
                    message="基金编号应用 ', No. xxx' 格式，不应放在括号中",
                    section=self.section_name,
                    paragraph_index=idx,
                    context=text[:100],
                    fixable=True,
                    suggestion="将 '(No.xxx)' 改为 ', No. xxx'",
                ))

            # 3.6.5 基金名称实词首字母大写
            if "supported by" in text.lower():
                after_by = text.split("by", 1)[-1].strip()
                # 跳过冗余 "This work..." 部分
                after_by = re.sub(r"^This\s+work\s+was\s+supported\s+by\s*", "", after_by, flags=re.IGNORECASE)
                words = after_by.split()
                for w in words[:5]:
                    clean_w = re.sub(r"[,;.]", "", w)
                    if clean_w and clean_w[0].islower() and clean_w not in ("and", "of", "the", "for", "in", "on", "to", "by"):
                        issues.append(Issue(
                            rule_id="3.6.5",
                            rule_name="基金名称大写",
                            severity=Severity.WARNING,
                            message=f"基金名称中 '{clean_w}' 首字母应大写",
                            section=self.section_name,
                            paragraph_index=idx,
                            context=text[:80],
                        ))
                        break

        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        from ..utils import regex_replace_in_paragraph

        if "冗余措辞" in issue.rule_name:
            pattern = re.compile(r"This\s+work\s+was\s+supported\s+by\s*", re.IGNORECASE)
            if regex_replace_in_paragraph(para, pattern, ""):
                issue.fix_description = "已删除冗余措辞 (已保留格式)"
                return True

        if "基金编号格式" in issue.rule_name:
            pattern = re.compile(r"\(No\.\s*(\w+)\)")
            if regex_replace_in_paragraph(para, pattern, r", No. \1"):
                issue.fix_description = "基金编号格式已修正 (已保留格式)"
                return True

        return False
