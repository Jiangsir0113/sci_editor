from docx import Document
from sci_editor.parser import parse_document
from sci_editor.engine import RuleEngine
from sci_editor.models import SectionType

def verify_italics():
    doc_path = "tests/reproduce_bug.docx"
    doc_struct = parse_document(doc_path)
    engine = RuleEngine()
    
    issues = engine.check(doc_struct)
    engine.fix_all(doc_struct, issues)
    
    print("--- Detailed Run Inspection ---")
    for i, para in enumerate(doc_struct.all_paragraphs):
        if not para.text.strip(): continue
        print(f"Para {i}: '{para.text}'")
        for j, run in enumerate(para.runs):
            print(f"  Run {j}: '{run.text}' [Italic: {run.italic}]")
            if run.text.strip() == "P" and run.italic:
                print(f"    SUCCESS: found italic P in para {i}")

if __name__ == "__main__":
    verify_italics()
