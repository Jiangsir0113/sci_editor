"""3.1 标题规则"""

import re
from typing import List
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure


# 不允许出现的缩略词白名单（这些可以出现在标题中）
TITLE_ABBREVIATION_WHITELIST = {
    "SARS-CoV-2", "COVID-19", "DNA", "RNA", "mRNA", "HIV", "AIDS",
    "CT", "MRI", "PET", "ICU", "ECMO",
}


class TitleWordCount(BaseRule):
    rule_id = "3.1.1"
    rule_name = "标题字数"
    section_name = "3.1 标题"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        title_text = doc.get_section_text(SectionType.TITLE)
        if not title_text:
            return []
        # 只取第一行作为真正标题
        title_line = title_text.strip().split("\n")[0].strip()
        # 移除 "Title: " 前缀
        title_line = re.sub(r"^(title\s*[:：]\s*)", "", title_line, flags=re.IGNORECASE).strip()
        word_count = len(title_line.split())
        if word_count > 18:
            return [Issue(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                severity=Severity.ERROR,
                message=f"标题超过18个单词（当前 {word_count} 个）",
                section=self.section_name,
                context=title_line,
                suggestion="请精简标题至18个单词以内",
            )]
        return []


class TitleStartWord(BaseRule):
    rule_id = "3.1.2"
    rule_name = "标题开头词"
    section_name = "3.1 标题"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        title_text = doc.get_section_text(SectionType.TITLE)
        if not title_text:
            return []
        title_line = title_text.strip().split("\n")[0].strip()
        title_line = re.sub(r"^(title\s*[:：]\s*)", "", title_line, flags=re.IGNORECASE).strip()
        first_word = title_line.split()[0].lower() if title_line.split() else ""
        if first_word in ("a", "an", "the"):
            return [Issue(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                severity=Severity.ERROR,
                message=f"标题不能以 '{first_word}' 开头",
                section=self.section_name,
                context=title_line,
                suggestion="请去掉标题开头的冠词",
            )]
        return []


class TitleCaseReport(BaseRule):
    rule_id = "3.1.3"
    rule_name = "Case Report 标题逻辑"
    section_name = "3.1 标题"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        title_text = doc.get_section_text(SectionType.TITLE)
        if not title_text:
            return []
        title_line = title_text.strip().split("\n")[0].strip().lower()
        issues = []
        if "case report" in title_line and "review of literature" in title_line:
            if doc.reference_count > 0 and doc.reference_count < 30:
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.WARNING,
                    message=f"参考文献仅 {doc.reference_count} 条（<30），标题应去掉 'review of literature'，仅保留 'A case report'",
                    section=self.section_name,
                    context=title_text.strip().split("\n")[0].strip(),
                    suggestion="去掉 'and review of literature'",
                ))
        return issues


class TitleColonCapital(BaseRule):
    rule_id = "3.1.5"
    rule_name = "标题冒号后大写"
    section_name = "3.1 标题"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        title_text = doc.get_section_text(SectionType.TITLE)
        if not title_text:
            return []
        title_line = title_text.strip().split("\n")[0].strip()
        title_line = re.sub(r"^(title\s*[:：]\s*)", "", title_line, flags=re.IGNORECASE).strip()
        issues = []
        # 查找冒号后的首字母
        matches = re.finditer(r":\s*([a-z])", title_line)
        for m in matches:
            issues.append(Issue(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                severity=Severity.ERROR,
                message=f"标题冒号后首字母 '{m.group(1)}' 应大写",
                section=self.section_name,
                context=title_line,
                fixable=True,
                suggestion=f"将 '{m.group(1)}' 改为 '{m.group(1).upper()}'",
            ))
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        section = doc.get_section(SectionType.TITLE)
        if not section:
            return False
        for _, para in section.paragraphs:
            for run in para.runs:
                if ":" in run.text:
                    run.text = re.sub(r":\s*([a-z])",
                                      lambda m: ": " + m.group(1).upper(),
                                      run.text)
                    issue.fix_description = "冒号后首字母已大写"
                    return True
        return False


class TitleAbbreviation(BaseRule):
    rule_id = "3.1.6"
    rule_name = "标题缩略词"
    section_name = "3.1 标题"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        title_text = doc.get_section_text(SectionType.TITLE)
        if not title_text:
            return []
        title_line = title_text.strip().split("\n")[0].strip()
        title_line = re.sub(r"^(title\s*[:：]\s*)", "", title_line, flags=re.IGNORECASE).strip()
        issues = []
        # 匹配全大写≥2字母的缩略词
        abbrevs = re.findall(r"\b([A-Z]{2,}(?:-[A-Z0-9]+)*)\b", title_line)
        for abbr in abbrevs:
            if abbr not in TITLE_ABBREVIATION_WHITELIST:
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.WARNING,
                    message=f"标题中含有缩略词 '{abbr}'，建议使用全称",
                    section=self.section_name,
                    context=title_line,
                    suggestion=f"将 '{abbr}' 替换为全称（除非是基因/蛋白名）",
                ))
        return issues
