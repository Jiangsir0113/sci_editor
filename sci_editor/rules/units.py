"""3.18 单位规则"""

import re
from typing import List
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure

# 常见计量单位列表
COMMON_UNITS = [
    "mg", "kg", "g", "µg", "ng", "pg",
    "mL", "dL", "µL", "nL",
    "mm", "cm", "m", "km", "µm", "nm",
    "mmHg", "kPa", "Pa",
    "mmol", "µmol", "nmol", "pmol", "mol",
    "mM", "µM", "nM",
    "Hz", "kHz", "MHz", "GHz",
    "min", "h", "s", "ms",
    "IU", "U",
    "Gy", "mGy",
    "°C", "K",
    "W", "kW", "mW",
    "V", "mV", "kV",
    "A", "mA",
]


class UnitSpacing(BaseRule):
    rule_id = "3.18.1"
    rule_name = "数字与单位间距"
    section_name = "3.18 单位"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        """数字和单位之间应有空格（除了°和%）"""
        body_text = doc.get_section_text(SectionType.BODY)
        if not body_text:
            return []
        issues = []
        for unit in COMMON_UNITS:
            # 查找数字紧跟单位（无空格）的情况
            pattern = r"(\d)" + re.escape(unit) + r"\b"
            matches = re.finditer(pattern, body_text)
            for m in matches:
                # 获取周围上下文
                start = max(0, m.start() - 10)
                end = min(len(body_text), m.end() + 10)
                context = body_text[start:end]
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.ERROR,
                    message=f"数字与单位 '{unit}' 之间应有空格",
                    section=self.section_name,
                    context=context,
                    fixable=True,
                ))
                break  # 每种单位只报告一次
        return issues


class LiterCapital(BaseRule):
    rule_id = "3.18.2"
    rule_name = "升大写L"
    section_name = "3.18 单位"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        """升的单位应大写: L"""
        body_text = doc.get_section_text(SectionType.BODY)
        if not body_text:
            return []
        issues = []
        # 检查小写 l 用作升的情况 (如 ml, dl 等)
        matches = re.findall(r"\b(\d+(?:\.\d+)?)\s*(ml|dl|µl|ul)\b", body_text, re.IGNORECASE)
        for num, unit in matches:
            if unit[-1] == "l":  # 小写 l
                correct = unit[:-1] + "L"
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.ERROR,
                    message=f"升的单位应使用大写 L: '{unit}' → '{correct}'",
                    section=self.section_name,
                    context=f"{num} {unit}",
                    fixable=True,
                    suggestion=f"改为 {correct}",
                ))
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        for section in doc.sections.values():
            for _, para in section.paragraphs:
                for run in para.runs:
                    # 替换小写l结尾的升单位
                    new_text = re.sub(r"\b(m|d|µ|u)l\b", lambda m: m.group(1) + "L", run.text)
                    if new_text != run.text:
                        run.text = new_text
                        changed = True
        if changed:
            issue.fix_description = "升单位已改为大写 L"
        return changed
