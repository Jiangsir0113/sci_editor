"""3.4 机构规则"""

import re
from typing import List
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure


class AffiliationFormat(BaseRule):
    rule_id = "3.4.4"
    rule_name = "机构格式"
    section_name = "3.4 机构"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        """检查机构格式: Department of ..., 机构, 城市 邮编, 国家"""
        aff_text = doc.get_section_text(SectionType.AFFILIATIONS)
        if not aff_text:
            return []
        issues = []
        for line in aff_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # 检查是否以实词首字母大写
            words = line.split(",")
            for w in words:
                w = w.strip()
                if w and w[0].islower() and not w.startswith("of ") and not w.startswith("and "):
                    issues.append(Issue(
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        severity=Severity.WARNING,
                        message=f"机构中实词 '{w[:30]}' 首字母应大写",
                        section=self.section_name,
                        context=line[:80],
                        fixable=True,
                    ))
                    break
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        
        old_text = para.text
        # 与 check 逻辑保持一致
        parts = old_text.split(",")
        new_parts = []
        for p in parts:
            stripped = p.lstrip()
            if not stripped:
                new_parts.append(p)
                continue
            
            indent = p[:p.find(stripped)]
            if stripped[0].islower() and not stripped.startswith("of ") and not stripped.startswith("and "):
                p = indent + stripped[0].upper() + stripped[1:]
            new_parts.append(p)
        
        new_text = ",".join(new_parts)
        if new_text == old_text:
            return False

        # 格式安全地替换整个段落文本
        # 由于机构行通常是一个单一格式（或简单的 Run），
        # 我们最简单的安全做法是找到包含第一个字母的 Run 并修改它
        changed = False
        pos = 0
        current_new_text = new_text
        
        # 这里采用简单的全局替换逻辑，但通过修改 Run 来实现
        # 如果段落只有一个 Run，直接修改
        if len(para.runs) == 1:
            para.runs[0].text = new_text
            changed = True
        from ..utils import regex_replace_in_paragraph
        # 构造匹配模式：匹配整行并替换为 new_text
        # 我们使用 regex_replace_in_paragraph 来安全地替换文本并保留格式
        def repl_fn(m): return new_text
        changed = regex_replace_in_paragraph(para, re.compile(".*", re.DOTALL), repl_fn)
        
        if changed:
            issue.fix_description = "机构中的小写词已首字母大写 (已保留格式)"
        return changed
        
        if changed:
            issue.fix_description = "机构中的小写词已首字母大写 (已保留格式)"
        return changed


class AffiliationDuplicateCheck(BaseRule):
    rule_id = "3.4.3"
    rule_name = "相同机构合并"
    section_name = "3.4 机构"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        """检查是否存在应合并的相同机构"""
        aff_text = doc.get_section_text(SectionType.AFFILIATIONS)
        if not aff_text:
            return []
        issues = []
        lines = [l.strip() for l in aff_text.strip().split("\n") if l.strip()]
        # 提取机构名（去掉作者名部分）
        departments = []
        for line in lines:
            # 尝试提取 "Department of..." 部分
            m = re.search(r"(Department\s+of\s+.+)", line, re.IGNORECASE)
            if m:
                departments.append((m.group(1).strip().lower(), line))

        # 查找相似但不完全相同的机构（可能因大小写/空格不同未合并）
        for i in range(len(departments)):
            for j in range(i + 1, len(departments)):
                d1, l1 = departments[i]
                d2, l2 = departments[j]
                # 简单检查：去掉空格后一样
                if re.sub(r"\s+", "", d1) == re.sub(r"\s+", "", d2) and d1 != d2:
                    issues.append(Issue(
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        severity=Severity.WARNING,
                        message="发现可能需要合并的相同机构（格式略有差异）",
                        section=self.section_name,
                        context=f"'{l1[:50]}...' vs '{l2[:50]}...'",
                        suggestion="请核实这两个机构是否相同，如相同则应合并",
                    ))
        return issues
