"""3.10 缩略词增强规则

核心逻辑：
1. 收集文档中所有的 Full Name (ABBR) 定义。
2. 对摘要、Core Tip、正文分别独立统计每个 ABBR 出现的总频次（包含其定义处的全称、后续缩写、以及未定义处的孤立全称）。
3. 如果 频次 >= 3：
   - 该部分第一处出现的术语必须是 "Full Name (ABBR)"。
   - 该部分后续出现的术语必须是 "ABBR"。
4. 如果 频次 < 3：
   - 该部分所有出现的术语必须是 "Full Name"。
   - 移除所有 "(ABBR)" 定义。
"""

import re
from typing import List, Dict, Set, Tuple
from ..engine import BaseRule
from ..models import Issue, Severity, SectionType, DocumentStructure
from ..utils import regex_replace_in_paragraph


class AbbreviationEnhancedRule(BaseRule):
    rule_id = "3.10.x"
    rule_name = "缩略词增强一致性"
    section_name = "3.10 缩略词"

    # 需要检查的区段
    SECTIONS_TO_CHECK = [
        (SectionType.ABSTRACT, "摘要"),
        (SectionType.CORE_TIP, "Core Tip"),
        (SectionType.BODY, "正文"),
    ]

    # 定义识别正则：放宽限制，允许第一个词大写后接后续词（不强制后续词也大写）
    # 匹配形态：Full Name (ABBR)
    ABBR_DEF_PATTERN = re.compile(r"([A-Z][a-zA-Z\s-]{5,})\s*\(([A-Z]{2,}(?:-[A-Z0-9]+)*)\)")

    def _collect_global_defs(self, doc: DocumentStructure) -> Dict[str, str]:
        """收集全文档所有的定义对 {ABBR: FullName}"""
        defs = {}
        for para in doc.all_paragraphs:
            found = self.ABBR_DEF_PATTERN.findall(para.text)
            for f, a in found:
                defs[a] = f.strip()
        return defs

    # 学术常用缩写白名单 (豁免 3 次频次限制)
    COMMON_ABBRS = {
        "DNA", "RNA", "PCR", "AIDS", "HIV", "CT", "MRI", "ECG", "EEG", "pH", 
        "mRNA", "siRNA", "tRNA", "ATP", "ADP", "AMP", "cAMP", "CD4", "CD8", 
        "IgG", "IgM", "IgA", "IgE", "TNF", "IL", "IFN", "TGF", "MAPK", "NF-κB"
    }

    def check(self, doc: DocumentStructure) -> List[Issue]:
        issues = []
        global_defs = self._collect_global_defs(doc)
        if not global_defs:
            return issues

        for st, label in self.SECTIONS_TO_CHECK:
            section = doc.get_section(st)
            if not section: continue
            
            text = section.raw_text
            for abbr, full in global_defs.items():
                # 1. 查找所有定义 (Full Name (ABBR))
                def_pattern = re.compile(re.escape(full) + r"\s*\(" + re.escape(abbr) + r"\)", re.IGNORECASE)
                defs_in_sec = list(def_pattern.finditer(text))
                
                # 2. 查找所有独立缩写
                abbr_pattern = re.compile(r"\b" + re.escape(abbr) + r"\b")
                abbrs_in_sec = list(abbr_pattern.finditer(text))
                
                # 3. 查找所有独立全称 (非定义的一部分)
                full_pattern = re.compile(r"\b" + re.escape(full) + r"\b", re.IGNORECASE)
                fulls_in_sec = list(full_pattern.finditer(text))
                
                # 排除定义中的全称和缩写
                actual_abbr_count = 0
                for a_match in abbrs_in_sec:
                    if not any(d.start() <= a_match.start() < d.end() for d in defs_in_sec):
                        actual_abbr_count += 1
                
                standalone_fulls = []
                for f_match in fulls_in_sec:
                    if not any(d.start() <= f_match.start() < d.end() for d in defs_in_sec):
                        standalone_fulls.append(f_match)

                # 总有效频次 = 定义次数 + 独立缩写次数 + 独立全称次数
                total_freq = len(defs_in_sec) + actual_abbr_count + len(standalone_fulls)
                
                if total_freq == 0: continue

                # --- 科学性改进逻辑 ---
                # 1. 白名单豁免：常用词不强制转回全称
                if abbr in self.COMMON_ABBRS:
                    continue
                
                # 2. 人工定义保护：如果作者手动写了 Full Name (ABBR) 定义，
                # 即使频次 < 3，我们也认为作者在该区段需要此缩写，予以保留。
                if len(defs_in_sec) > 0 and total_freq < 3:
                    continue

                if total_freq < 3:
                    # 应该全部使用全称，并移除定义 (仅针对那些“无定义但用了缩写”或“频次过低且无必要”的情况)
                    if len(defs_in_sec) > 0 or actual_abbr_count > 0:
                        issues.append(Issue(
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            severity=Severity.INFO,
                            message=f"术语 '{abbr}' 在{label}中仅出现 {total_freq} 次，且非公认常用缩写，建议统一为全称",
                            section=self.section_name,
                            context=f"{abbr} (freq={total_freq})",
                            fixable=True,
                            paragraph_index=-1
                        ))
                else:
                    # 应该：第一处定义，后续缩写
                    # 先找该区段第一处出现术语的位置
                    all_hits = [] # List[(start, type)]  type: 'def', 'abbr', 'full'
                    for d in defs_in_sec: all_hits.append((d.start(), 'def', d))
                    for a in abbrs_in_sec:
                        # 排除定义中的
                        if any(d.start() <= a.start() < d.end() for d in defs_in_sec): continue
                        all_hits.append((a.start(), 'abbr', a))
                    for f in standalone_fulls: all_hits.append((f.start(), 'full', f))
                    
                    all_hits.sort(key=lambda x: x[0])
                    
                    if not all_hits: continue
                    
                    first_pos, first_type, first_match = all_hits[0]
                    
                    # 检查点 1: 第一处是否为定义
                    if first_type != 'def':
                        # 找出第一处所在段落
                        para_idx = -1
                        current_len = 0
                        for p_idx, p_obj in section.paragraphs:
                            if current_len <= first_pos < current_len + len(p_obj.text) + 1:
                                para_idx = p_idx
                                break
                            current_len += len(p_obj.text) + 1
                            
                        issues.append(Issue(
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            severity=Severity.WARNING,
                            message=f"术语 '{abbr}' 在{label}中频次 >= 3，首次出现应提供定义 '{full} ({abbr})'",
                            section=self.section_name,
                            context=first_match.group(0),
                            fixable=True,
                            paragraph_index=para_idx
                        ))
                    
                    # 检查点 2: 后续是否均为缩写
                    other_hits = all_hits[1:]
                    for pos, h_type, m in other_hits:
                        if h_type != 'abbr':
                            para_idx = -1
                            current_len = 0
                            for p_idx, p_obj in section.paragraphs:
                                if current_len <= pos < current_len + len(p_obj.text) + 1:
                                    para_idx = p_idx
                                    break
                                current_len += len(p_obj.text) + 1
                                
                            issues.append(Issue(
                                rule_id=self.rule_id,
                                rule_name=self.rule_name,
                                severity=Severity.WARNING,
                                message=f"术语 '{abbr}' 在{label}中已定义，后续应统一使用缩写",
                                section=self.section_name,
                                context=m.group(0),
                                fixable=True,
                                paragraph_index=para_idx
                            ))
        return issues

    def fix(self, doc: DocumentStructure, issue: Issue) -> bool:
        global_defs = self._collect_global_defs(doc)
        m_abbr = re.search(r"术语 '([^']+)'", issue.message)
        if not m_abbr: return False
        abbr = m_abbr.group(1)
        full = global_defs.get(abbr)
        if not full: return False

        # 确定区段
        target_st = None
        for st, label in self.SECTIONS_TO_CHECK:
            if label in issue.message:
                target_st = st
                break
        if not target_st: return False
        
        section = doc.get_section(target_st)
        if not section: return False

        changed = False

        if "仅出现" in issue.message:
            # 逻辑：总频次 < 3，统一改回全称，移除所有定义
            def_pattern = re.compile(re.escape(full) + r"\s*\(" + re.escape(abbr) + r"\)", re.IGNORECASE)
            abbr_pattern = re.compile(r"\b" + re.escape(abbr) + r"\b")
            
            for _, para in section.paragraphs:
                # 先处理定义 (ABCD (AB) -> ABCD)
                if regex_replace_in_paragraph(para, def_pattern, lambda m: full):
                    changed = True
                # 再处理孤立缩写 (AB -> ABCD)
                if regex_replace_in_paragraph(para, abbr_pattern, lambda m: full):
                    changed = True
        
        elif "首次出现应提供定义" in issue.message or "后续应统一使用缩写" in issue.message:
            # 逻辑：频次 >= 3，第一处改为定义，后续改为缩写
            # 这需要全区段协同修复。为了避免多次 fix 重复操作，我们一次性扫描全区段。
            first_found_global = False
            
            def_pattern_raw = re.escape(full) + r"\s*\(" + re.escape(abbr) + r"\)"
            # 我们需要匹配三种形态：定义、全称、缩写
            # 综合正则
            combined_pattern = re.compile(rf"{def_pattern_raw}|\b{re.escape(abbr)}\b|\b{re.escape(full)}\b", re.IGNORECASE)
            
            for _, para in section.paragraphs:
                def repl_fn(m):
                    nonlocal first_found_global
                    if not first_found_global:
                        first_found_global = True
                        return f"{full} ({abbr})"
                    else:
                        return abbr
                
                if regex_replace_in_paragraph(para, combined_pattern, repl_fn):
                    changed = True
                    
        return changed

# 保持向后兼容：如果需要特定名称
class AbbreviationSectionFrequency(AbbreviationEnhancedRule): pass
class AbbreviationConsistency(AbbreviationEnhancedRule): pass
class AbbreviationFrequency(AbbreviationEnhancedRule): pass
