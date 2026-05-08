from typing import List, Dict
from sci_editor.models import Issue, DocumentStructure


def build_diff(doc: DocumentStructure, issues: List[Issue]) -> List[Dict]:
    """
    将 issues 按 paragraph_index 分组，生成前端需要的 diff 数据。
    suggestion 字段允许包含受控 HTML 标签（em, strong, sup, sub）。
    """
    by_para: Dict[int, List[Issue]] = {}
    for issue in issues:
        if issue.paragraph_index >= 0:
            by_para.setdefault(issue.paragraph_index, []).append(issue)

    diff = []
    for para_idx, para_issues in sorted(by_para.items()):
        if para_idx >= len(doc.all_paragraphs):
            continue
        original_text = doc.all_paragraphs[para_idx].text
        fixable = [i for i in para_issues if i.fixable and i.suggestion]
        modified_text = fixable[0].suggestion if fixable else original_text
        diff.append({
            "paragraph_index": para_idx,
            "original": original_text,
            "modified": modified_text,
            "issue_ids": [i.rule_id + "_" + str(para_idx) for i in para_issues],
        })
    return diff
