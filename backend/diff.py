from typing import List, Dict, Any
from sci_editor.models import Issue, DocumentStructure


def build_diff(doc: DocumentStructure, issues_with_ids: List[Dict[str, Any]]) -> List[Dict]:
    """
    将 issues 按 paragraph_index 分组，生成前端需要的 diff 数据。
    issues_with_ids 是包含 'issue_id' 和原始 Issue 对象 ('issue') 的字典列表。
    suggestion 字段允许包含受控 HTML 标签（em, strong, sup, sub）。
    """
    by_para: Dict[int, List[Dict]] = {}
    for item in issues_with_ids:
        issue = item["issue"]
        if issue.paragraph_index >= 0:
            by_para.setdefault(issue.paragraph_index, []).append(item)

    diff = []
    for para_idx, para_items in sorted(by_para.items()):
        if para_idx >= len(doc.all_paragraphs):
            continue
        original_text = doc.all_paragraphs[para_idx].text
        fixable = [it for it in para_items if it["issue"].fixable and it["issue"].suggestion]
        modified_text = fixable[0]["issue"].suggestion if fixable else original_text
        diff.append({
            "paragraph_index": para_idx,
            "original": original_text,
            "modified": modified_text,
            "issue_ids": [it["issue_id"] for it in para_items],
        })
    return diff
