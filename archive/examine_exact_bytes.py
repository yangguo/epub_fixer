#!/usr/bin/env python3
"""
Examine exact byte content of problematic meta tags
"""

import os
import zipfile

def extract_and_examine():
    # Extract the EPUB
    with zipfile.ZipFile('doing2.epub', 'r') as zip_ref:
        zip_ref.extractall('byte_examine')
    
    # Read the cover.xhtml file
    filepath = 'byte_examine/OEBPS/cover.xhtml'
    
    with open(filepath, 'rb') as f:
        content_bytes = f.read()
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content_text = f.read()
    
    lines = content_text.split('\n')
    
    print("=== Examining cover.xhtml ===")
    print(f"Total lines: {len(lines)}")
    
    # Look at line 6 (index 5)
    if len(lines) > 5:
        line6 = lines[5]
        print(f"\nLine 6 content: '{line6}'")
        print(f"Line 6 length: {len(line6)}")
        
        # Show character at position 66 (index 65)
        if len(line6) > 65:
            char_at_66 = line6[65]
            print(f"Character at column 66: '{char_at_66}' (ASCII: {ord(char_at_66)})")
            
            # Show surrounding characters
            start = max(0, 60)
            end = min(len(line6), 70)
            surrounding = line6[start:end]
            print(f"Characters 61-70: '{surrounding}'")
            
            # Show each character with its position
            print("\nCharacter breakdown around column 66:")
            for i in range(start, end):
                if i < len(line6):
                    char = line6[i]
                    ascii_val = ord(char)
                    marker = " <-- COLUMN 66" if i == 65 else ""
                    print(f"  Position {i+1:2d}: '{char}' (ASCII: {ascii_val:3d}){marker}")
        
        # Look for the meta tag pattern
        print("\n=== Meta tag analysis ===")
        import re
        meta_pattern = r'<meta[^>]*/>'
        matches = re.finditer(meta_pattern, content_text)
        
        for i, match in enumerate(matches):
            print(f"\nMeta tag {i+1}:")
            print(f"  Content: '{match.group()}'")
            print(f"  Start position: {match.start()}")
            print(f"  End position: {match.end()}")
            
            # Find which line this is on
            text_before = content_text[:match.start()]
            line_num = text_before.count('\n') + 1
            line_start = text_before.rfind('\n') + 1
            col_num = match.start() - line_start + 1
            print(f"  Line {line_num}, Column {col_num}")
            
            # Check for spaces before />
            tag_content = match.group()
            if '/>' in tag_content:
                before_close = tag_content.split('/>')[0]
                trailing_spaces = len(before_close) - len(before_close.rstrip())
                print(f"  Trailing spaces before '/>': {trailing_spaces}")
    
    # Clean up
    import shutil
    shutil.rmtree('byte_examine')

if __name__ == '__main__':
    extract_and_examine()