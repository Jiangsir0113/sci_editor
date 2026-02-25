import re
from docx.text.paragraph import Paragraph
from docx.enum.text import WD_COLOR_INDEX

def copy_run_format(source_run, target_run):
    """
    Copies font formatting from source_run to target_run.
    """
    target_run.bold = source_run.bold
    target_run.italic = source_run.italic
    target_run.underline = source_run.underline
    
    font = source_run.font
    target_font = target_run.font
    
    if font.name:
        target_font.name = font.name
    if font.size:
        target_font.size = font.size
    if font.color and font.color.rgb:
        target_font.color.rgb = font.color.rgb
    
    # Handle highlight color if possible
    try:
        target_font.highlight_color = font.highlight_color
    except:
        pass

def regex_replace_in_paragraph(para: Paragraph, pattern: re.Pattern, repl_fn, occurrences: int = 0):
    """
    A robust regex replacement that handles matches spanning multiple runs 
    while preserving formatting for the parts of strings that aren't changed.
    
    If occurrences > 0, only replace up to that many matches.
    """
    text = para.text
    all_matches = list(pattern.finditer(text))
    if not all_matches:
        return False
    
    if occurrences > 0:
        matches = all_matches[:occurrences]
    else:
        matches = all_matches

    changed = False
    # Process matches in reverse to avoid index shifting
    for m in reversed(matches):
        start_pos = m.start()
        end_pos = m.end()
        orig_text = m.group(0)
        if callable(repl_fn):
            new_text = repl_fn(m)
        else:
            new_text = repl_fn
        
        if orig_text == new_text:
            continue
            
        # Identify runs involved
        pos = 0
        matching_runs_indices = []
        for i, run in enumerate(para.runs):
            run_len = len(run.text)
            run_start = pos
            run_end = pos + run_len
            
            if not (run_end <= start_pos or run_start >= end_pos):
                matching_runs_indices.append(i)
            pos = run_end
            
        if not matching_runs_indices:
            continue
            
        # Strategy: 
        # 1. Modify the first run to contain its prefix + the new text.
        # 2. Clear or truncate subsequent runs involved in the match.
        # 3. If the match ended in the middle of a run, preserve that run's suffix.
        
        first_idx = matching_runs_indices[0]
        last_idx = matching_runs_indices[-1]
        
        first_run = para.runs[first_idx]
        last_run = para.runs[last_idx]
        
        # Calculate offsets within first and last run
        current_pos = 0
        for i in range(first_idx):
            current_pos += len(para.runs[i].text)
        
        offset_in_first = start_pos - current_pos
        
        current_pos = 0
        for i in range(last_idx):
            current_pos += len(para.runs[i].text)
        offset_in_last = end_pos - current_pos
        
        prefix = first_run.text[:offset_in_first]
        suffix = last_run.text[offset_in_last:]
        
        # Update first run
        first_run.text = prefix + new_text
        
        # If it's the same run, just append suffix
        if first_idx == last_idx:
            first_run.text += suffix
        else:
            # Multi-run match
            # Clear intermediate runs
            for i in range(first_idx + 1, last_idx):
                para.runs[i].text = ""
            # Set the last run to just its suffix
            last_run.text = suffix
            
        changed = True
        
    return changed
