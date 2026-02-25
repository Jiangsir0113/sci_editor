"""3.25-3.26 图注与表格规则

- 图注标题不能有缩略词
- 表格 P value 大写
- 表格单元格末尾无句号
- 表格注释缩略词格式 OR: ...; CI: ...;
- 表格注释 Model 1 -> 上标 1
"""

import re
from typing import List
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure


class FigureCaptionCheck(BaseRule):
    rule_id = "3.25"
    rule_name = "图注检查"
    section_name = "3.25 图"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        fig_section = doc.get_section(SectionType.FIGURES)
        if not fig_section:
            return []
        issues = []

        for idx, para in fig_section.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            # 3.25.4 标题不能有缩略词
            m = re.match(r"^(Figure|Fig\.?)\s+\d+\s+(.*?)[\.\n]", text, re.IGNORECASE)
            if m:
                caption_title = m.group(2)
                abbrs = re.findall(r"\b([A-Z]{2,})\b", caption_title)
                for abbr in abbrs:
                    if abbr not in {"CT", "MRI", "PET", "DNA", "RNA", "HIV", "COVID", "SARS"}:
                        issues.append(Issue(
                            rule_id="3.25.4",
                            rule_name="图注标题缩略词",
                            severity=Severity.WARNING,
                            message=f"图注标题中含有缩略词 '{abbr}'，标题中不应使用缩略词",
                            section=self.section_name,
                            paragraph_index=idx,
                            context=text[:80],
                        ))
        return issues


class TableFormatCheck(BaseRule):
    rule_id = "3.26"
    rule_name = "表格格式"
    section_name = "3.26 表格"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        issues = []

        # 检查每个表格
        for t_idx, table in enumerate(doc.tables):
            for r_idx, row in enumerate(table.rows):
                for c_idx, cell in enumerate(row.cells):
                    text = cell.text.strip()
                    if re.search(r"\bp\s*value", text):
                        issues.append(Issue(
                            rule_id="3.26.4",
                            rule_name="P value 大写",
                            severity=Severity.ERROR,
                            message="表格中 'p value' 的 'P' 应大写",
                            section=self.section_name,
                            context=text[:60],
                            fixable=True,
                            # 存储位置信息以便 fix
                            extra_info={"table_idx": t_idx, "row_idx": r_idx, "cell_idx": c_idx}
                        ))
                    if re.search(r"\bMean\s*±", text):
                        issues.append(Issue(
                            rule_id="3.26.6",
                            rule_name="mean ± SD 格式",
                            severity=Severity.WARNING,
                            message="表格中 'Mean ± SD' 的 'mean' 首字母不需要大写",
                            section=self.section_name,
                            context=text[:60],
                            fixable=True,
                            extra_info={"table_idx": t_idx, "row_idx": r_idx, "cell_idx": c_idx}
                        ))

        # 检查表格下方的注释段落
        tables_section = doc.get_section(SectionType.TABLES)
        if tables_section:
            for idx, para in tables_section.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                
                # 检查缩略词分隔符：应使用冒号和分号
                if re.search(r"\b([A-Z]{2,}),\s+[a-z]", text):
                    issues.append(Issue(
                        rule_id="3.26.9",
                        rule_name="表格注释缩写格式",
                        severity=Severity.WARNING,
                        message="表格注释中缩写与全称之间建议用冒号 ':' 分隔，各条目间用分号 ';'",
                        section=self.section_name,
                        paragraph_index=idx,
                        context=text[:80],
                        fixable=True,
                    ))

                # 检查 Model 1 格式 -> 应使用上标 1
                if re.search(r"Model\s+(\d+)", text):
                    issues.append(Issue(
                        rule_id="3.26.10",
                        rule_name="表格 Model 注释",
                        severity=Severity.INFO,
                        message="表格注释中的 'Model 1' 等建议使用上标编号",
                        section=self.section_name,
                        paragraph_index=idx,
                        context=text[:80],
                    ))

        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        from ..utils import regex_replace_in_paragraph

        if "表格注释缩写格式" in issue.rule_name:
            idx = issue.paragraph_index
            if idx < 0 or idx >= len(doc.all_paragraphs):
                return False
            para = doc.all_paragraphs[idx]
            pattern = re.compile(r"\b([A-Z]{2,}),\s+")
            if regex_replace_in_paragraph(para, pattern, r"\1: "):
                issue.fix_description = "已将逗号替换为冒号 (已保留格式)"
                return True

        if "P value 大写" in issue.rule_name or "mean ± SD 格式" in issue.rule_name:
            if not issue.extra_info:
                return False
            t_idx = issue.extra_info.get("table_idx")
            r_idx = issue.extra_info.get("row_idx")
            c_idx = issue.extra_info.get("cell_idx")
            
            if t_idx is None or r_idx is None or c_idx is None:
                return False
                
            table = doc.tables[t_idx]
            cell = table.rows[r_idx].cells[c_idx]
            
            changed = False
            if "P value 大写" in issue.rule_name:
                pattern = re.compile(r"\bp\s*value", re.IGNORECASE)
                for para in cell.paragraphs:
                    if regex_replace_in_paragraph(para, pattern, "P value"):
                        changed = True
            
            if "mean ± SD 格式" in issue.rule_name:
                pattern = re.compile(r"\bMean\s*±", re.IGNORECASE)
                for para in cell.paragraphs:
                    if regex_replace_in_paragraph(para, pattern, "mean ±"):
                        changed = True
                        
            if changed:
                issue.fix_description = "单元格格式已修正 (已保留格式)"
                return True

        return False
