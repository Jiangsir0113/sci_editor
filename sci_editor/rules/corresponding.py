"""3.7 通讯作者规则

- 姓名, 职称, 科室, 医院, 地址. 邮箱
- 邮箱小写
- 去除重复信息（如 Department 重复）
"""

import re
from typing import List
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure


class CorrespondingAuthorFormat(BaseRule):
    rule_id = "3.7"
    rule_name = "通讯作者格式"
    section_name = "3.7 通讯作者"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        issues = []
        section = doc.get_section(SectionType.CORRESPONDING)
        if not section:
            return []
            
        for idx, para in section.paragraphs:
            text = para.text
            # 3.7.1 检查邮箱小写
            emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
            for email in emails:
                if email != email.lower():
                    issues.append(Issue(
                        rule_id="3.7.4",
                        rule_name="邮箱小写",
                        severity=Severity.ERROR,
                        message=f"邮箱 '{email}' 应全部小写",
                        section=self.section_name,
                        paragraph_index=idx,
                        context=email,
                        fixable=True,
                        suggestion=f"改为 '{email.lower()}'",
                    ))

            # 3.7.2 检查冗余：Department 重复出现
            if len(re.findall(r"Department\s+of", text, re.IGNORECASE)) > 1:
                issues.append(Issue(
                    rule_id="3.7.5",
                    rule_name="信息冗余",
                    severity=Severity.WARNING,
                    message="通讯作者信息中存在冗余的科室(Department)信息，建议合并",
                    section=self.section_name,
                    paragraph_index=idx,
                    context=text[:100],
                    suggestion="合并重复的部门和地址信息",
                ))

        # 3.7.3 检查格式：姓名, 职称, 科室, 医院, 地址. 邮箱
        # 简单检查是否有多个段落（通常应一人一行，如果是多人，格式应统一）
        # 这里在 section 级别检查
        corr_text = doc.get_section_text(SectionType.CORRESPONDING)
        paras = corr_text.strip().split("\n")
        if len(paras) > 1:
            addresses = set()
            for p in paras:
                m = re.search(r",\s*([^,.]+\d{5,}[^,.]*)", p)
                if m:
                    addr = m.group(1).strip()
                    if addr in addresses:
                        issues.append(Issue(
                            rule_id="3.7.6",
                            rule_name="地址冗余",
                            severity=Severity.WARNING,
                            message=f"通讯作者中地址 '{addr}' 重复出现，建议合并",
                            section=self.section_name,
                        ))
                    addresses.add(addr)

        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        from ..utils import regex_replace_in_paragraph

        if "邮箱" in issue.rule_name:
            pattern = re.compile(re.escape(issue.context))
            if regex_replace_in_paragraph(para, pattern, issue.context.lower()):
                issue.fix_description = "邮箱已修改为小写 (已保留格式)"
                return True

        return False
