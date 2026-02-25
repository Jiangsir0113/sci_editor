from docx import Document
from sci_editor.parser import parse_document
from sci_editor.engine import RuleEngine
from sci_editor.models import SectionType

def test_fixes():
    doc_path = "tests/未修改.docx"
    doc_struct = parse_document(doc_path)
    engine = RuleEngine()
    
    print("--- Running Check ---")
    issues = engine.check(doc_struct)
    
    ci_issues = [i for i in issues if "95%CI" in i.message]
    print(f"Found {len(ci_issues)} CI issues.")
    for i in ci_issues[:3]:
        print(f"  - {i.message} (Fixable: {i.fixable})")
        
    abbr_issues = [i for i in issues if "3.10" in i.rule_id]
    print(f"Found {len(abbr_issues)} Abbreviation issues.")
    for i in abbr_issues[:3]:
        print(f"  - {i.message} (Fixable: {i.fixable})")

    print("\n--- Running Fix ---")
    fixed_count = engine.fix_all(doc_struct, issues)
    print(f"Fixed {fixed_count} issues.")

    print("\n--- Verifying Fixed Content ---")
    # Check a few specific paragraphs if possible
    # For abbreviation consistency (3.10.2)
    found_consistency_fix = False
    for p in doc_struct.all_paragraphs:
        if "OGTT" in p.text and "oral glucose tolerance test" not in p.text:
            # If we replaced full name with OGTT after definition
            found_consistency_fix = True
    
    print(f"Abbreviation consistency fix applied: {found_consistency_fix}")

    # Verify CI fix
    found_ci_fix = False
    for p in doc_struct.all_paragraphs:
        if "95%CI: 0.73-0.95, P = 0.005" in p.text:
            found_ci_fix = True
    print(f"CI P-value fix applied: {found_ci_fix}")

if __name__ == "__main__":
    test_fixes()
