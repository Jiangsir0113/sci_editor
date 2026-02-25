"""Verification script to run the sci_editor tool on local files."""
import os
import sys

# Add project root to path
PROJECT_ROOT = r'd:\AI_Project'
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sci_editor.parser import parse_document
from sci_editor.engine import RuleEngine
from sci_editor.reporter import generate_text_report

def run_verification():
    input_file = os.path.join(PROJECT_ROOT, 'tests', '未修改.docx')
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    print(f"--- Processing {input_file} ---")
    
    # 1. Parse
    doc_struct = parse_document(input_file)
    print(f"Sections found: {list(doc_struct.sections.keys())}")
    print(f"Manuscript type: {doc_struct.manuscript_type}")

    # 2. Check
    engine = RuleEngine()
    print(f"Rules loaded: {len(engine.rules)}")
    
    issues = engine.check(doc_struct)
    
    # 3. Report before fix
    print("\n=== Issues Found ===")
    report_before = generate_text_report(issues, "未修改.docx (Before fix)")
    # Avoid UnicodeEncodeError on GBK terminals
    try:
        print(report_before)
    except UnicodeEncodeError:
        print(report_before.encode('ascii', 'ignore').decode('ascii'))

    # 4. Fix
    fixed_count = engine.fix_all(doc_struct, issues)
    print(f"\nFixed {fixed_count} issues.")

    # 5. Save and check again
    output_file = os.path.join(PROJECT_ROOT, 'tests', '已修复_verify.docx')
    doc_struct.word_doc.save(output_file)
    print(f"Saved fixed document to {output_file}")

    # Re-parse and check the fixed document
    doc_struct_fixed = parse_document(output_file)
    issues_after = engine.check(doc_struct_fixed)
    
    print("\n=== Remaining Issues after Auto-Fix ===")
    report_after = generate_text_report(issues_after, "已修复_verify.docx")
    try:
        print(report_after)
    except UnicodeEncodeError:
        print(report_after.encode('ascii', 'ignore').decode('ascii'))

if __name__ == "__main__":
    run_verification()
