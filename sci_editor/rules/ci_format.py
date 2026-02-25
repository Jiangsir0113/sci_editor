"""规则 3.15 扩展 — 置信区间格式 & OR 格式检查与修复

正确格式：
  - OR = 0.79 （OR 后加等号和空格）
  - 95%CI: 0.64-0.98 （冒号+连字符/to）
"""

import re
from ..models import Issue, Severity, SectionType, DocumentStructure
from ..engine import BaseRule


def _fix_ci_format(m: re.Match) -> str:
    """基于 Match 对象标准化 CI 格式"""
    text = m.group(0)
    
    # 核心转换逻辑：95%CI (0.73, 0.95, P = 0.005) -> 95%CI: 0.73-0.95, P = 0.005
    # 匹配模式：95%CI (lo, hi, P) 或者 95%CI (lo, hi), P
    sub_pattern = r"(95\s*%\s*CI)\s*[:：]?\s*[（(\[]\s*(-?[\d.]+)\s*[,，]\s*(-?[\d.]+)\s*[）)\]](?:\s*[,，]\s*(P\s*[=<>≤≥]\s*[\d.]+))?|(95\s*%\s*CI)\s*[:：]?\s*[（(\[]\s*(-?[\d.]+)\s*[,，]\s*(-?[\d.]+)(?:\s*[,，]\s*(P\s*[=<>≤≥]\s*[\d.]+))\s*[）)\]]"
    
    match_data = re.search(sub_pattern, text, re.IGNORECASE)
    
    if match_data:
        # 情况 1: (lo, hi), P
        if match_data.group(1):
            prefix, lo_str, hi_str, p_val = match_data.group(1, 2, 3, 4)
        # 情况 2: (lo, hi, P)
        else:
            prefix, lo_str, hi_str, p_val = match_data.group(5, 6, 7, 8)
            
        prefix = "95%CI"
        try:
            lo, hi = float(lo_str), float(hi_str)
            sep = " to " if (lo < 0 or hi < 0) else "-"
        except ValueError:
            sep = "-"
        
        result = f"{prefix}: {lo_str}{sep}{hi_str}"
        if p_val:
            p_val_fixed = re.sub(r"^[pP]", "P", p_val.strip())
            p_val_fixed = re.sub(r"P\s*([=<>≤≥])\s*", r"P \1 ", p_val_fixed)
            result += f", {p_val_fixed}"
        return result

    # 处理缺失冒号的情况：95%CI 0.6-0.8 -> 95%CI: 0.6-0.8
    if re.search(r"95\s*%\s*CI\s+\d", text, re.IGNORECASE):
        # 还要看是否带尾随 P
        p_match = re.search(r"P\s*[=<>≤≥]\s*[\d.]+", text, re.IGNORECASE)
        main_part = re.sub(r"95\s*%\s*CI\s+", "95%CI: ", text, flags=re.IGNORECASE)
        # 移除 P 部分（后面统一加）
        main_part = re.sub(r"\s*[,，]\s*P\s*[=<>≤≥]\s*[\d.]+", "", main_part, flags=re.IGNORECASE)
        
        if p_match:
            p_val = p_match.group(0)
            p_val_fixed = re.sub(r"^[pP]", "P", p_val.strip())
            p_val_fixed = re.sub(r"P\s*([=<>≤≥])\s*", r"P \1 ", p_val_fixed)
            return f"{main_part.strip()}, {p_val_fixed}"
        return main_part.strip()

    return re.sub(r"95\s*%\s*CI", "95%CI", text, flags=re.IGNORECASE)


def _fix_or_format(m: re.Match) -> str:
    """基于 Match 对象标准化 OR 格式"""
    # OR 0.5 -> OR = 0.5
    # OR=0.5 -> OR = 0.5
    val = m.group(2)
    return f"OR = {val}"


from ..utils import regex_replace_in_paragraph

class CIFormatRule(BaseRule):
    rule_id = "3.15.3"
    rule_name = "置信区间格式"
    section_name = "3.15 范围与百分比"
    
    # 增强版：支持多种组合，包括尾随 P 值
    CI_ERR_PATTERN = re.compile(r"95\s*%\s*CI\s*(?:[:：]?\s*[（(\[]\s*-?[\d.]+\s*[,，]\s*-?[\d.]+(?:\s*[,，]\s*P\s*[=<>≤≥]\s*[\d.]+)?\s*[）)\]]|\s+(?![:：])\d+\.?\d*[-]\d+\.?\d*)(?:\s*[,，]\s*P\s*[=<>≤≥]\s*[\d.]+)?", re.IGNORECASE)

    def check(self, doc: DocumentStructure):
        issues = []
        body = doc.get_section(SectionType.BODY)
        abstract = doc.get_section(SectionType.ABSTRACT)

        for section in [s for s in [body, abstract] if s]:
            for idx, para in section.paragraphs:
                for m in self.CI_ERR_PATTERN.finditer(para.text):
                    issues.append(Issue(
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        severity=Severity.ERROR,
                        message=f"置信区间格式错误：'{m.group(0)}'",
                        section=section.section_type.value,
                        paragraph_index=idx,
                        context=m.group(0),
                        fixable=True,
                        suggestion="应使用 '95%CI: num-num' 格式",
                    ))
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        
        # 应用 CI 格式修复 (保留格式)
        changed = regex_replace_in_paragraph(para, self.CI_ERR_PATTERN, _fix_ci_format)
        
        if changed:
            # 恢复统计符号斜体
            from .statistics import STAT_PATTERN, _split_and_italicize
            text = para.text
            for m in STAT_PATTERN.finditer(text):
                _split_and_italicize(para, m.group(1), m.start())
            
            issue.fix_description = "CI 格式已修正 (已保留格式)"
            return True
        return False


class ORFormatRule(BaseRule):
    rule_id = "3.15.4"
    rule_name = "OR 格式"
    section_name = "3.15 范围与百分比"

    OR_ERR_PATTERN = re.compile(r"\bOR\s*(=?)\s*(\d+\.?\d*)")

    def check(self, doc: DocumentStructure):
        issues = []
        body = doc.get_section(SectionType.BODY)
        abstract = doc.get_section(SectionType.ABSTRACT)

        for section in [s for s in [body, abstract] if s]:
            for idx, para in section.paragraphs:
                for m in self.OR_ERR_PATTERN.finditer(para.text):
                    if m.group(0) != f"OR = {m.group(2)}":
                        issues.append(Issue(
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            severity=Severity.ERROR,
                            message=f"OR 格式错误：'{m.group(0)}'",
                            section=section.section_type.value,
                            paragraph_index=idx,
                            context=m.group(0),
                            fixable=True,
                            suggestion=f"应为 'OR = {m.group(2)}'",
                        ))
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        
        if regex_replace_in_paragraph(para, self.OR_ERR_PATTERN, _fix_or_format):
            issue.fix_description = "OR 格式已修正 (已保留格式)"
            return True
        return False
