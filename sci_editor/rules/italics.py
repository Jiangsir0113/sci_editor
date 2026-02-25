"""3.21 斜体规则"""

import re
from typing import List
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure

# 需要斜体的词汇
ITALIC_WORDS = []


def _split_run_for_italic(para, run_idx, word):
    """
    在指定 Run 中找到 word 并将其拆分为独立的斜体 Run。
    返回是否进行了修改。
    """
    run = para.runs[run_idx]
    text = run.text
    # 查找单词（忽略大小写，但保留原大小写）
    pattern = re.compile(re.escape(word), re.IGNORECASE)
    match = pattern.search(text)
    if not match:
        return False

    start, end = match.span()
    before_text = text[:start]
    word_text = text[start:end]
    after_text = text[end:]

    # 如果 word 已经是整个 Run 且已经是斜体，跳过
    if not before_text and not after_text and run.italic:
        return False

    # 拆分逻辑
    # 1. 更新当前 Run 为 before_text
    run.text = before_text
    
    # 2. 插入 word_run
    word_run = para.add_run(word_text)
    word_run.italic = True
    # 复制原始 run 的其他格式（如加粗）
    word_run.bold = run.bold
    
    # 3. 插入 after_run
    after_run = para.add_run(after_text)
    after_run.italic = run.italic
    after_run.bold = run.bold

    # 注意：python-docx 的 add_run 总是添加到段落末尾。
    # 我们需要手动调整 XML 元素的顺序。
    p = para._p
    r_word = word_run._r
    r_after = after_run._r
    r_orig = run._r
    
    p.insert(p.index(r_orig) + 1, r_word)
    p.insert(p.index(r_word) + 1, r_after)

    return True


class ItalicWords(BaseRule):
    rule_id = "3.21"
    rule_name = "斜体词"
    section_name = "3.21 斜体"

    def check(self, doc: DocumentStructure) -> List[Issue]:
        """检查需要斜体的词汇是否已设为斜体"""
        issues = []
        checked_sections = [
            SectionType.BODY,
            SectionType.ABSTRACT,
            SectionType.CORE_TIP,
        ]

        for section_type in checked_sections:
            section = doc.get_section(section_type)
            if not section:
                continue

            for _, para in section.paragraphs:
                text = para.text
                for word in ITALIC_WORDS:
                    # 使用正则匹配独立单词，避免匹配到 word 内部（如 "viable" 中的 "via"）
                    pattern = re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
                    for m in pattern.finditer(text):
                        # 检查匹配位置所在的 Run
                        pos = 0
                        is_italic = False
                        for run in para.runs:
                            if pos <= m.start() < pos + len(run.text):
                                is_italic = run.italic
                                break
                            pos += len(run.text)
                        
                        if not is_italic:
                            issues.append(Issue(
                                rule_id=self.rule_id,
                                rule_name=self.rule_name,
                                severity=Severity.ERROR,
                                message=f"'{word}' 应设为斜体",
                                section=self.section_name,
                                context=text[max(0, m.start()-20):m.end()+20],
                                fixable=True,
                                paragraph_index=_,
                                suggestion=f"将 '{word}' 设为斜体",
                            ))
                            break # 每词每段只报一次

        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        """将需要斜体的词设为斜体，采用拆分 Run 的方式"""
        idx = issue.paragraph_index
        if idx < 0 or idx >= len(doc.all_paragraphs):
            return False
        
        para = doc.all_paragraphs[idx]
        changed = False
        
        # 重新扫描段落中的词
        for word in ITALIC_WORDS:
            pattern = re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
            # 由于 fix 时可能修改 runs 列表，我们需要小心处理
            # 简化做法：每次只修一个，或者重新获取 text
            text = para.text
            match = pattern.search(text)
            if match:
                # 寻找对应的 Run
                pos = 0
                for r_idx, run in enumerate(para.runs):
                    if pos <= match.start() < pos + len(run.text):
                        if _split_run_for_italic(para, r_idx, match.group(0)):
                            changed = True
                            break
                    pos += len(run.text)
        
        if changed:
            issue.fix_description = "斜体词已通过拆分 Run 修正"
        return changed
