"""3.16 数字格式规则"""

import re
from typing import List
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure


class NumberFormat(BaseRule):
    rule_id = "3.16"
    rule_name = "数字格式"
    section_name = "3.16 数字"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        issues = []
        body = doc.get_section(SectionType.BODY)
        if not body:
            return issues
            
        for idx, para in body.paragraphs:
            text = para.text
            # 查找带逗号分隔的数字 (e.g., 10,089,600)
            # 使用 finditer 以便进行位置相关的过滤
            for m in re.finditer(r"\b(\d{1,3}(?:,\d{3})+)\b", text):
                val = m.group(1)
                start = m.start()
                
                # 核心改进：排除参考文献引用 (e.g., [122,123])
                # 简单启发式：检查该匹配是否位于 [ ] 之间，且中间内容复合引用特征
                pre_text = text[:start]
                post_text = text[m.end():]
                
                if '[' in pre_text and ']' in post_text:
                    last_bracket_open = pre_text.rfind('[')
                    next_bracket_close = post_text.find(']')
                    # 如果匹配被一对最近的 [] 包围
                    if last_bracket_open != -1 and next_bracket_close != -1:
                        # 且中间内容主要由数字、逗号、连字符、空格组成
                        between = text[last_bracket_open : m.end() + next_bracket_close + 1]
                        if re.match(r"\[[\d,\s-]+\]", between):
                            # print(f"DEBUG: Skipping number match '{val}' as part of citation '{between}'")
                            continue

                clean = val.replace(",", "")
                issues.append(Issue(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.ERROR,
                    message=f"数字 '{val}' 不应使用逗号分隔",
                    section=self.section_name,
                    paragraph_index=idx,
                    context=val,
                    fixable=True,
                    suggestion=f"改为 {clean}",
                ))
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        para = doc.all_paragraphs[idx]
        from ..utils import regex_replace_in_paragraph
        
        # 精确匹配该数字
        pattern = re.compile(re.escape(issue.context))
        clean = issue.context.replace(",", "")
        
        if regex_replace_in_paragraph(para, pattern, clean):
            issue.fix_description = f"已去掉逗号: {clean} (已保留格式)"
            return True
        return False
