"""3.3 作者名字规则

- 中国大陆作者名字应为 Jia-Ping Yan 格式
- 自动修复 PeiYi → Pei-Yi, HuaLan → Hua-Lan
- 中间名缩写后不应加点
"""

import re
from typing import List
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure


def _split_camelcase_chinese(name: str) -> str:
    """将驼峰式中国名字转为连字符格式
    PeiYi → Pei-Yi, NanFang → Nan-Fang, HuaLan → Hua-Lan, ZiHao → Zi-Hao
    """
    # 匹配大写字母开头的音节段
    parts = re.findall(r"[A-Z][a-z]+", name)
    if len(parts) >= 2:
        return "-".join(parts)
    return name


class ChineseAuthorNameFormat(BaseRule):
    rule_id = "3.3.1"
    rule_name = "中国作者名字格式"
    section_name = "3.3 作者"

    # 匹配驼峰式或连字符格式但第二部分为小写的中国名
    # PeiYi, NanFang (驼峰) 或 Tai-xian, Pei-yi (连字符小写)
    CAMEL_OR_HYPHEN_PATTERN = re.compile(
        r"\b([A-Z][a-z]+(?:[A-Z][a-z]+|-[a-z]+))\b"
    )

    def check(self, doc: DocumentStructure) -> List[Issue]:
        issues = []
        # 检查 AUTHORS 和 AFFILIATIONS 部分
        for section_type in [SectionType.AUTHORS, SectionType.AFFILIATIONS]:
            section = doc.get_section(section_type)
            if not section:
                continue
            for idx, para in section.paragraphs:
                text = para.text
                for m in self.CAMEL_OR_HYPHEN_PATTERN.finditer(text):
                    original_name = m.group(1)
                    fixed = self._fix_name_format(original_name)
                    if fixed != original_name:
                        issues.append(Issue(
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            severity=Severity.ERROR,
                            message=f"作者名 '{original_name}' 格式不规范，应改为 '{fixed}'",
                            section=self.section_name,
                            paragraph_index=idx,
                            context=original_name,
                            fixable=True,
                            suggestion=f"改为 '{fixed}'",
                        ))
        return issues

    def _fix_name_format(self, name: str) -> str:
        """处理 PeiYi -> Pei-Yi 或 Tai-xian -> Tai-Xian"""
        if "-" in name:
            # 处理 Tai-xian -> Tai-Xian
            parts = name.split("-")
            if len(parts) == 2:
                return f"{parts[0]}-{parts[1].capitalize()}"
        else:
            # 处理 PeiYi -> Pei-Yi
            return _split_camelcase_chinese(name)
        return name

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        from ..utils import regex_replace_in_paragraph
        
        # 精确匹配该名字
        pattern = re.compile(r"\b" + re.escape(issue.context) + r"\b")
        fixed = self._fix_name_format(issue.context)
        
        if regex_replace_in_paragraph(para, pattern, fixed):
            issue.fix_description = f"'{issue.context}' → '{fixed}' (已保留格式)"
            return True
        return False


class ForeignAuthorMiddleNameDot(BaseRule):
    rule_id = "3.3.2"
    rule_name = "外国作者中间名缩写"
    section_name = "3.3 作者"

    PATTERN = re.compile(r"\b([A-Z])\.\s+([A-Z][a-z]+)")

    def check(self, doc: DocumentStructure) -> List[Issue]:
        """中间名缩写后不应加点"""
        section = doc.get_section(SectionType.AUTHORS)
        if not section:
            return []
        issues = []
        for idx, para in section.paragraphs:
            for m in self.PATTERN.finditer(para.text):
                initial, surname = m.groups()
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.ERROR,
                    message=f"作者中间名缩写 '{initial}.' 后不应加点",
                    section=self.section_name,
                    paragraph_index=idx,
                    context=m.group(),
                    fixable=True,
                    suggestion=f"将 '{initial}.' 改为 '{initial}'",
                ))
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        from ..utils import regex_replace_in_paragraph
        
        def repl_fn(m):
            return f"{m.group(1)} {m.group(2)}"
            
        if regex_replace_in_paragraph(para, self.PATTERN, repl_fn):
            issue.fix_description = "中间名缩写的点已移除 (已保留格式)"
            return True
        return False


class SingleLetterNameWarning(BaseRule):
    rule_id = "3.3.3"
    rule_name = "单字母名字警告"
    section_name = "3.3 作者"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        """单字母名字需要核实"""
        author_text = doc.get_section_text(SectionType.AUTHORS)
        if not author_text:
            return []
        issues = []
        # 匹配 "P Park" 模式
        matches = re.findall(r"\b([A-Z])\s+([A-Z][a-z]{2,})\b", author_text)
        for initial, surname in matches:
            issues.append(Issue(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                severity=Severity.WARNING,
                message=f"作者名 '{initial} {surname}' 仅有一个字母，请核实是否正确",
                section=self.section_name,
                context=f"{initial} {surname}",
            ))
        return issues
