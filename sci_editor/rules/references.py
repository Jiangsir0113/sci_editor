"""3.23 参考文献规则

- 参考文献按序引用
- PMID/DOI 检测
- 作者名 et al 检查
- 期刊名称应为斜体
- 引用中句号分隔错误 [1.2] → [1,2]
"""

import re
from typing import List
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure


class ReferenceSequentialCitation(BaseRule):
    rule_id = "3.23.1"
    rule_name = "参考文献按序引用"
    section_name = "3.23 参考文献"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        """所有参考文献需要按顺序在正文全部引用"""
        body_text = doc.get_section_text(SectionType.BODY)
        if not body_text:
            return []
        issues = []

        cited_nums = set()
        for m in re.finditer(r"\[(\d[\d,\s-]*)\]", body_text):
            inner = m.group(1)
            for part in inner.split(","):
                part = part.strip()
                if "-" in part:
                    bounds = part.split("-")
                    if len(bounds) == 2 and bounds[0].strip().isdigit() and bounds[1].strip().isdigit():
                        for i in range(int(bounds[0].strip()), int(bounds[1].strip()) + 1):
                            cited_nums.add(i)
                elif part.isdigit():
                    cited_nums.add(int(part))

        if doc.reference_count > 0:
            for i in range(1, doc.reference_count + 1):
                if i not in cited_nums:
                    issues.append(Issue(
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        severity=Severity.ERROR,
                        message=f"参考文献 [{i}] 未在正文中引用",
                        section=self.section_name,
                    ))

        ordered_citations = []
        for m in re.finditer(r"\[(\d+)\]", body_text):
            num = int(m.group(1))
            if num not in ordered_citations:
                ordered_citations.append(num)

        for i in range(1, len(ordered_citations)):
            if ordered_citations[i] < ordered_citations[i-1] - 5:
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.WARNING,
                    message=f"引用顺序可能不正确：[{ordered_citations[i-1]}] 之后出现了 [{ordered_citations[i]}]",
                    section=self.section_name,
                ))

        return issues


class ReferencePMIDCheck(BaseRule):
    rule_id = "3.23.2"
    rule_name = "PMID/DOI检测"
    section_name = "3.23 参考文献"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        ref_section = doc.get_section(SectionType.REFERENCES)
        if not ref_section:
            return []
        issues = []

        current_ref_num = 0
        current_ref_text = ""

        for _, para in ref_section.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            m = re.match(r"^(\d+)\s+(.*)", text)
            if m:
                if current_ref_num > 0 and current_ref_text:
                    self._check_single_ref(current_ref_num, current_ref_text, issues)
                current_ref_num = int(m.group(1))
                current_ref_text = m.group(2)
            else:
                current_ref_text += " " + text

        if current_ref_num > 0 and current_ref_text:
            self._check_single_ref(current_ref_num, current_ref_text, issues)

        return issues

    def _check_single_ref(self, num: int, text: str, issues: List[Issue]):
        has_pmid = bool(re.search(r"PMID\s*[:：]?\s*\d+", text, re.IGNORECASE))
        has_doi = bool(re.search(r"DOI\s*[:：]?\s*\S+", text, re.IGNORECASE))
        has_doi2 = bool(re.search(r"10\.\d{4,}/", text))

        if not has_pmid and not has_doi and not has_doi2:
            issues.append(Issue(
                rule_id="3.23.4",
                rule_name="无PMID高亮",
                severity=Severity.WARNING,
                message=f"参考文献 [{num}] 缺少 PMID 和 DOI",
                section=self.section_name,
                context=text[:80],
                suggestion="请查询并补充 PMID 或 DOI",
            ))


class ReferenceAuthorEtAl(BaseRule):
    rule_id = "3.23.3"
    rule_name = "参考文献作者格式"
    section_name = "3.23 参考文献"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        """参考文献中作者名需要全部显示，不能用 et al 代替"""
        ref_section = doc.get_section(SectionType.REFERENCES)
        if not ref_section:
            return []
        issues = []

        for _, para in ref_section.paragraphs:
            text = para.text.strip()
            if re.search(r"\bet\s+al\b", text, re.IGNORECASE):
                m = re.match(r"^(\d+)\s+", text)
                ref_num = m.group(1) if m else "?"
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.ERROR,
                    message=f"参考文献 [{ref_num}] 不应使用 'et al' 缩写，需列出全部作者",
                    section=self.section_name,
                    context=text[:80],
                ))

        return issues


class ReferenceJournalItalic(BaseRule):
    rule_id = "3.23.5"
    rule_name = "参考文献期刊名斜体"
    section_name = "3.23 参考文献"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        """参考文献中期刊名称应为斜体"""
        ref_section = doc.get_section(SectionType.REFERENCES)
        if not ref_section:
            return []
        issues = []

        for idx, para in ref_section.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            m = re.match(r"^(\d+)\s+", text)
            if not m:
                continue
            ref_num = m.group(1)

            # 期刊名通常出现在年份之后：...2024; 15: 123 或 ...2024. Title. Journal Year
            # WJG 参考格式：Author. Title. Journal Year; Vol: Pages [PMID: xxx DOI: xxx]
            # 提取期刊名：在最后一个句号前的部分（Year 之前）
            # 简化：检查是否有任何 run 是斜体（期刊名应该是斜体的）
            has_italic_journal = False
            for run in para.runs:
                # 期刊名 run 通常是斜体的
                if run.italic and run.text.strip() and len(run.text.strip()) > 1:
                    # 排除统计符号等单字符斜体
                    has_italic_journal = True
                    break

            if not has_italic_journal and len(text) > 30:
                # 尝试找到期刊名位置（年份前的部分）
                # 典型格式：...authored text. JournalName Year; Vol: Pages
                journal_match = re.search(
                    r"\.\s*([A-Z][A-Za-z\s]+?)\s+\d{4}\s*;",
                    text
                )
                if journal_match:
                    journal_name = journal_match.group(1).strip()
                    issues.append(Issue(
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        severity=Severity.WARNING,
                        message=f"参考文献 [{ref_num}] 的期刊名 '{journal_name}' 应为斜体",
                        section=self.section_name,
                        paragraph_index=idx,
                        context=text[:80],
                        fixable=True,
                        suggestion=f"将 '{journal_name}' 设为斜体",
                    ))

        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False

        para = doc.all_paragraphs[idx]
        text = para.text

        # 找到期刊名
        journal_match = re.search(
            r"\.\s*([A-Z][A-Za-z\s]+?)\s+\d{4}\s*;",
            text
        )
        if not journal_match:
            return False

        journal_name = journal_match.group(1).strip()

        # 在 runs 中找到期刊名并设斜体
        for run in para.runs:
            if journal_name in run.text or any(
                word in run.text for word in journal_name.split()[:2]
            ):
                run.italic = True
                issue.fix_description = f"期刊名 '{journal_name}' 已设为斜体"
                return True

        return False
