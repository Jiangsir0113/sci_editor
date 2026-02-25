from sci_editor.parser import parse_document
from sci_editor.models import SectionType

def diag():
    doc_path = "tests/未修改.docx"
    doc_struct = parse_document(doc_path)
    
    print(f"Total paragraphs: {len(doc_struct.all_paragraphs)}")
    
    # Check sections
    for st, section in doc_struct.sections.items():
        print(f"Section {st}: {len(section.paragraphs)} paragraphs")
        if st == SectionType.AFFILIATIONS:
            for idx, p in section.paragraphs:
                print(f"  [{idx}] {p.text[:100]}")
    
    print("\n--- FIRST 20 PARAGRAPHS ---")
    # We can't easily see the labels from ds directly unless we re-run the labels part or check where each p is
    labels = {}
    for st, section in doc_struct.sections.items():
        for idx, p in section.paragraphs:
            labels[idx] = st
            
    for i in range(min(40, len(doc_struct.all_paragraphs))):
        text = doc_struct.all_paragraphs[i].text.strip()
        label = labels.get(i, "UNKNOWN")
        print(f"[{i}] ({label}) {text[:100]}")

if __name__ == "__main__":
    diag()
