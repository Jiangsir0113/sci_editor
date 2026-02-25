"""规则 3.28 — 正文词语大写检查

规则：
- EMBASE 在正文中需大写（不接受 Embase、embase 等）
- 正文中除特定词（缩略词、首句首字母、标题等）外，非首字母用小写
- 本模块聚焦于已知必须全大写的词汇检查
"""

import re
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure
from ..utils import regex_replace_in_paragraph


# 必须全部大写的词汇（及其错误写法映射）
# 使用字典而非列表，key = 正确写法，value = 正则匹配错误变体的模式
MUST_BE_UPPERCASE = [
    "EMBASE",   # Embase, embase → EMBASE
    "CNKI",     # cnki, Cnki → CNKI
]

# 编译模式：匹配上述词汇的任何大小写变体（但排除全大写正确的）
def _build_patterns():
    pats = {}
    for word in MUST_BE_UPPERCASE:
        # 匹配与该词字母相同但非全大写的形式
        pat = re.compile(
            r"(?<!\w)" + "".join(f"[{c.upper()}{c.lower()}]" for c in word) + r"(?!\w)",
        )
        pats[word] = pat
    return pats


UPPERCASE_PATTERNS = _build_patterns()


class UppercaseKeywordsRule(BaseRule):
    rule_id = "3.28"
    rule_name = "特定词大写"
    section_name = "3.28 大小写"

    def check(self, doc: DocumentStructure):
        issues = []
        body = doc.get_section(SectionType.BODY)
        abstract = doc.get_section(SectionType.ABSTRACT)

        for section in [s for s in [body, abstract] if s]:
            for idx, para in section.paragraphs:
                text = para.text
                for correct_word, pat in UPPERCASE_PATTERNS.items():
                    for m in pat.finditer(text):
                        found = m.group(0)
                        if found != correct_word:
                            issues.append(Issue(
                                rule_id=self.rule_id,
                                rule_name=self.rule_name,
                                severity=Severity.ERROR,
                                message=f"'{found}' 应写为 '{correct_word}'（全大写）",
                                section=section.section_type.value,
                                paragraph_index=idx,
                                context=text[max(0, m.start()-20):m.end()+20],
                                suggestion=f"将 '{found}' 改为 '{correct_word}'",
                                fixable=True,
                            ))

        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False

        para = doc.all_paragraphs[idx]
        changed = False

        for correct_word, pat in UPPERCASE_PATTERNS.items():
            def repl_fn(m):
                # Only replace if the found text is not already the correct_word
                return correct_word if m.group(0) != correct_word else m.group(0)

            if regex_replace_in_paragraph(para, pat, repl_fn):
                changed = True

        if changed:
            issue.fix_description = "特定词已修正为全大写 (已保留格式)"
        return changed
