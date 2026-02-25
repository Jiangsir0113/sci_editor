"""3.2 短标题 (Running Title) 规则

格式要求：第一作者姓 et al. 标题内容
  - 'et al' 应为斜体
  - '&' 应替换为 'and'
  - 约6个单词
"""

import re
from typing import List
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure


class RunningTitleFormat(BaseRule):
    rule_id = "3.2.1"
    rule_name = "短标题格式"
    section_name = "3.2 短标题"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        rt_text = doc.get_section_text(SectionType.RUNNING_TITLE)
        if not rt_text:
            return []
        rt_line = rt_text.strip().split("\n")[0].strip()
        # 移除前缀
        rt_content = re.sub(r"^(running\s+title|short\s+title)\s*[:：]\s*",
                          "", rt_line, flags=re.IGNORECASE).strip()
        
        issues = []
        
        # 检查 & 应替换为 and
        if " & " in rt_content:
            issues.append(Issue(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                severity=Severity.ERROR,
                message="短标题中 '&' 应替换为 'and'",
                section=self.section_name,
                context=" & ",
                fixable=True,
                suggestion="将 '&' 替换为 'and'",
            ))

        # 检查格式：第一作者姓 + 名首字母组合 + et al.
        prefix = self._get_expected_prefix(doc)
        if prefix and not rt_content.startswith(prefix):
            issues.append(Issue(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                severity=Severity.WARNING,
                message=f"短标题应以 '{prefix}' 开头",
                section=self.section_name,
                context=rt_content[:20],
                fixable=True,
                suggestion=f"添加前缀 '{prefix}'",
            ))
        elif prefix and prefix in rt_content:
            # 检查 et al 是否为斜体
            section = doc.get_section(SectionType.RUNNING_TITLE)
            if section:
                for _, para in section.paragraphs:
                    if "et al" in para.text:
                        # 检查是否有非斜体的 et al
                        has_italic_error = False
                        for run in para.runs:
                            if "et al" in run.text and not run.italic:
                                has_italic_error = True
                                break
                        if has_italic_error:
                            issues.append(Issue(
                                rule_id=self.rule_id,
                                rule_name=self.rule_name,
                                severity=Severity.WARNING,
                                message="'et al' 应为斜体",
                                section=self.section_name,
                                context="et al",
                                fixable=True,
                                suggestion="将 'et al' 设为斜体",
                            ))

        # 检查长度
        word_count = len(rt_content.split())
        if word_count > 10:  # 加上作者后放宽一点
            issues.append(Issue(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                severity=Severity.WARNING,
                message=f"短标题过长（当前 {word_count} 个单词，建议约6-8个）",
                section=self.section_name,
                context=rt_content,
            ))

        return issues

    def _get_expected_prefix(self, doc: DocumentStructure) -> str:
        """获取预期的前缀，例如 'Song TX et al. '"""
        authors_text = doc.get_section_text(SectionType.AUTHORS)
        if not authors_text:
            return ""
        
        # 简单提取第一个作者名
        first_author = authors_text.split(",")[0].strip()
        if not first_author:
            return ""
            
        # 解析姓名 (假设格式为 Jia-Ping Yan 或 Yan JP)
        # 如果包含连字符，通常是 Jia-Ping Yan (First-Middle Last)
        if "-" in first_author:
            parts = first_author.split()
            if len(parts) >= 2:
                last_name = parts[-1]
                # 提取前一部分的首字母
                first_parts = parts[0].split("-")
                initials = "".join(p[0].upper() for p in first_parts if p)
                return f"{last_name} {initials} et al. "
        else:
            # 可能是 Yan JP 或 John Doe
            parts = first_author.split()
            if len(parts) >= 2:
                # 如果最后一部分全是斜体/全大写，可能是姓
                # 简单逻辑：假设最后一部分是姓
                last_name = parts[-1]
                first_name = parts[0]
                # 简单取首字母
                initials = "".join(p[0].upper() for p in parts[:-1] if p)
                return f"{last_name} {initials} et al. "
        
        return ""

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        section = doc.get_section(SectionType.RUNNING_TITLE)
        if not section:
            return False

        from ..utils import regex_replace_in_paragraph
        from .statistics import _split_and_italicize

        if "'&'" in issue.message:
            for _, para in section.paragraphs:
                if regex_replace_in_paragraph(para, re.compile(r" & "), " and "):
                    issue.fix_description = "'&' 已替换为 'and'"
                    return True

        if "开头" in issue.message:
            prefix = self._get_expected_prefix(doc)
            if not prefix: return False
            for _, para in section.paragraphs:
                # 移除可能存在的 Running Title: 前缀
                text = para.text
                clean_text = re.sub(r"^(running\s+title|short\s+title)\s*[:：]\s*",
                                 "", text, flags=re.IGNORECASE).strip()
                # 避免重复添加
                if not clean_text.startswith(prefix):
                    # 直接修改第一个 Run 的 text 会丢失格式，
                    # 最好是用 regex_replace_in_paragraph 替换开头
                    # 或者如果原本就是空的/非目标文本，直接插入。
                    # 这里我们用一个 trick：将第一个词替换为 Prefix + 第一个词
                    first_word = clean_text.split()[0] if clean_text.split() else ""
                    if first_word:
                        pattern = re.compile(re.escape(first_word))
                        if regex_replace_in_paragraph(para, pattern, prefix + first_word, occurrences=1):
                            # 接下来需要把 et al 设为斜体
                            _split_and_italicize(para, "et al", para.text.find("et al"))
                            issue.fix_description = f"已补全前缀 '{prefix}' 并设置斜体"
                            return True
                    else:
                        # 空段落处理
                        para.text = prefix
                        _split_and_italicize(para, "et al", 0)
                        return True

        if "斜体" in issue.message:
            changed = False
            for _, para in section.paragraphs:
                pos = para.text.find("et al")
                if pos != -1:
                    if _split_and_italicize(para, "et al", pos):
                        changed = True
            if changed:
                issue.fix_description = "'et al' 已设为斜体 (已保留格式)"
            return changed
            
        return False
