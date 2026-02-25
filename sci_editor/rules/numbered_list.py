"""规则 3.17 — 分点列表格式检查与修复

规则：
- 编号格式：(1) 空格 首字母大写...
- 每项之间用"; "（分号+空格）连接
- 最后一项前加 "and"
- 后括号 ) 后跟空格
"""

import re
from ..models import Issue, Severity, SectionType, DocumentStructure
from ..engine import BaseRule


# 匹配分点段落的模式：包含 (1) ... (2) ... 的段落
NUMBERED_LIST_PATTERN = re.compile(
    r"\(\s*1\s*\).+\(\s*2\s*\)",
    re.DOTALL,
)

# 单项格式：(n) 后面跟空格+大写首字母
ITEM_PATTERN = re.compile(r"\(\s*(\d+)\s*\)\s*([a-z])?")


def _check_paragraph(para_text: str):
    """返回 (issues_desc_list, fixed_text or None)"""
    problems = []
    if not NUMBERED_LIST_PATTERN.search(para_text):
        return problems, None

    # 检查每个 (n) 后首字母
    for m in ITEM_PATTERN.finditer(para_text):
        letter = m.group(2)
        if letter and letter.islower():
            problems.append(
                f"分项 ({m.group(1)}) 后首字母应大写（当前为 '{letter}'）"
            )

    # 检查分项之间应用 "; " 连接（而非 ". " 或 "," 等）
    # 简单检测：寻找 ); (n) 或 ) (n) 之间的分隔符
    sep_pattern = re.compile(r"\)\s*([^(\n]{0,5})\s*\((\d+)\)")
    for m in sep_pattern.finditer(para_text):
        sep = m.group(1).strip()
        item_num = m.group(2)
        if sep not in (";", "; ") and not sep.endswith(";"):
            problems.append(
                f"分项之间应用 '; ' 连接（分项 {item_num} 前的分隔符为 '{sep}'）"
            )

    # 检查最后一项前是否有 "and"
    # 找最后一个 (n)
    items = list(re.finditer(r"\(\s*\d+\s*\)", para_text))
    if len(items) >= 2:
        last_item = items[-1]
        before_last = para_text[items[-2].end():last_item.start()]
        if "and" not in before_last.lower():
            problems.append("最后一个分项前应加 'and'")

    return problems, None


class NumberedListRule(BaseRule):
    rule_id = "3.17"
    rule_name = "分点列表格式"
    section_name = "3.17 分点列表"

    def check(self, doc: DocumentStructure):
        issues = []
        body = doc.get_section(SectionType.BODY)
        if not body:
            return issues

        for idx, para in body.paragraphs:
            text = para.text
            if not NUMBERED_LIST_PATTERN.search(text):
                continue

            problems, _ = _check_paragraph(text)
            for prob in problems:
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.WARNING,
                    message=prob,
                    section=self.section_name,
                    paragraph_index=idx,
                    context=text[:120],
                    suggestion="参考格式：(1) Xxx; (2) Xxx; and (3) Xxx.",
                    fixable=False,
                ))

        return issues
