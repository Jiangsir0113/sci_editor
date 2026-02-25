import sys
import os
sys.path.append(os.getcwd())

from sci_editor.parser import parse_document
from sci_editor.rules.ci_format import CIFormatRule, ORFormatRule
from sci_editor.models import SectionType

def test_fix():
    doc_path = "tests/未修改.docx"
    doc = parse_document(doc_path)
    
    ci_rule = CIFormatRule()
    or_rule = ORFormatRule()
    
    issues = ci_rule.check(doc)
    print(f"Found {len(issues)} CI issues.")
    for issue in issues:
        print(f"  Issue: {issue.message} at para {issue.paragraph_index}")
        success = ci_rule.fix(doc, issue)
        print(f"  Fix success: {success}")
        if success:
            para = doc.all_paragraphs[issue.paragraph_index]
            print(f"  Fixed text: {para.text}")

    or_issues = or_rule.check(doc)
    print(f"Found {len(or_issues)} OR issues.")
    for issue in or_issues:
        print(f"  Issue: {issue.message} at para {issue.paragraph_index}")
        success = or_rule.fix(doc, issue)
        print(f"  Fix success: {success}")

if __name__ == "__main__":
    test_fix()
