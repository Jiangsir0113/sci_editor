"""规则 3.27 — 正文标题格式检查

规则：
- 一级标题：全大写 + 加粗 + 下划线（如 INTRODUCTION）
- 二级标题：斜体 + 加粗（如 Study design and subjects）
- 三级标题：加粗 + 冒号，紧跟正文（如 Inclusion criteria:）
- 标题不应有编号（如 "1. Introduction" 是错误的）
- 显著性分析部分只能用 "Statistical analysis" 作为二级标题
"""

import re
from docx.oxml.ns import qn
from ..models import Issue, Severity, SectionType, DocumentStructure
from ..engine import BaseRule


# 已知的一级标题
LEVEL1_TITLES = {
    "INTRODUCTION", "MATERIALS AND METHODS", "RESULTS", "DISCUSSION",
    "CONCLUSION", "METHODS", "BACKGROUND", "REFERENCES",
    "ACKNOWLEDGMENTS", "ACKNOWLEDGEMENTS",
}

# 常见的二级标题文本（非全大写，较短，通常独占一行）
LEVEL2_KNOWN_TITLES = {
    "study design", "study design and subjects",
    "data collection", "coffee consumption",
    "statistical analysis", "statistical analyses",
    "literature search", "literature search strategy",
    "study selection", "data extraction",
    "quality assessment", "quality of evidence",
    "inclusion criteria", "exclusion criteria",
    "study participants", "study population",
    "characteristics of participants",
    "sensitivity analysis", "subgroup analysis",
    "stratified analysis", "correlation analysis",
    "ethical approval", "ethical considerations",
}

# 已知的二级标题模式（部分）
STAT_TITLE_PATTERN = re.compile(
    r"(statistic|statistical)\s+(analysis|method|approach)",
    re.IGNORECASE,
)

NUMBERED_HEADING_PATTERN = re.compile(r"^\d+[.\s]\s*\w+")


def _para_is_bold(para) -> bool:
    """判断段落是否加粗（所有非空 run 都加粗）"""
    runs = [r for r in para.runs if r.text.strip()]
    if not runs:
        return False
    return all(r.bold for r in runs)


def _para_is_italic(para) -> bool:
    runs = [r for r in para.runs if r.text.strip()]
    if not runs:
        return False
    return all(r.italic for r in runs)


def _para_is_underline(para) -> bool:
    runs = [r for r in para.runs if r.text.strip()]
    if not runs:
        return False
    return all(r.underline for r in runs)


def _para_is_all_caps(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return len(letters) > 0 and all(c.isupper() for c in letters)


def _is_likely_level2_heading(text: str) -> bool:
    """判断文本是否像是二级标题"""
    stripped = text.strip()
    # 移除可能的前导编号
    clean = re.sub(r"^\d+\.?\d*\s*", "", stripped).strip()
    lower = clean.lower()

    # 已知的二级标题
    if lower in LEVEL2_KNOWN_TITLES:
        return True

    # 短段落（通常 < 8 单词），非全大写，不以句号结尾
    word_count = len(clean.split())
    if (word_count <= 8 and
        not _para_is_all_caps(clean) and
        not clean.endswith(".") and
        not clean.endswith(":") and
        clean[0].isupper()):
        # 仅标题式大写或很短的非句子段落
        return True

    return False


class HeadingFormatRule(BaseRule):
    rule_id = "3.27"
    rule_name = "正文标题格式"
    section_name = "3.27 标题格式"

    def check(self, doc: DocumentStructure):
        issues = []
        body = doc.get_section(SectionType.BODY)
        if not body:
            return issues

        for idx, para in body.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            # 检查编号标题
            if NUMBERED_HEADING_PATTERN.match(text) and len(text.split()) <= 8:
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.WARNING,
                    message=f"标题不应含编号：'{text[:60]}'",
                    section=self.section_name,
                    paragraph_index=idx,
                    context=text[:80],
                    suggestion="去除标题前的数字编号",
                    fixable=False,
                ))

            # [已取消] 一级和二级标题格式检查已应要求取消

            # 检查 Statistical analysis 标题
            if STAT_TITLE_PATTERN.search(text) and len(text.split()) <= 4:
                expected = "Statistical analysis"
                if text != expected:
                    issues.append(Issue(
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        severity=Severity.WARNING,
                        message=f"显著性分析部分的二级标题应为 'Statistical analysis'，当前为 '{text}'",
                        section=self.section_name,
                        paragraph_index=idx,
                        context=text,
                        suggestion=f"改为 'Statistical analysis'",
                        fixable=True,
                    ))

        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False

        para = doc.all_paragraphs[idx]
        text = para.text.strip()

        # [已取消] 修复一级/二级标题格式逻辑已移除

        # 修复 Statistical analysis
        if "Statistical analysis" in issue.message and STAT_TITLE_PATTERN.search(text):
            for run in para.runs:
                run.text = ""
            if para.runs:
                para.runs[0].text = "Statistical analysis"
                para.runs[0].italic = True
                para.runs[0].bold = True
            issue.fix_description = "已修正为 'Statistical analysis'"
            return True

        return False
