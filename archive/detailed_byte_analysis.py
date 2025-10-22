#!/usr/bin/env python3
"""
Detailed byte-level analysis of the problematic meta tag
"""

import os

def analyze_file(filepath):
    print(f"=== Analyzing {filepath} ===")
    
    with open(filepath, 'rb') as f:
        content_bytes = f.read()
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content_text = f.read()
    
    lines = content_text.split('\n')
    
    # Look at line 4 (index 3) - the problematic line for titlepage.xhtml
    if len(lines) > 3:
        line4 = lines[3]
        print(f"\nLine 4: '{line4}'")
        print(f"Length: {len(line4)}")
        
        # Show each character with position
        print("\nCharacter breakdown:")
        for i, char in enumerate(line4):
            ascii_val = ord(char)
            marker = " <-- COLUMN 70" if i == 69 else ""
            print(f"  Pos {i+1:2d}: '{char}' (ASCII: {ascii_val:3d}){marker}")
        
        # Look for non-printable characters
        print("\nNon-printable characters:")
        for i, char in enumerate(line4):
            if ord(char) < 32 or ord(char) > 126:
                print(f"  Position {i+1}: '{char}' (ASCII: {ord(char)})")
        
        # Show hex representation around column 70
        if len(line4) > 65:
            start = max(0, 65)
            end = min(len(line4), 80)
            segment = line4[start:end]
            print(f"\nHex around column 70:")
            for i, char in enumerate(segment):
                pos = start + i + 1
                hex_val = hex(ord(char))
                marker = " <-- COL 70" if pos == 70 else ""
                print(f"  Pos {pos:2d}: '{char}' = {hex_val}{marker}")
        
        # Check for specific problematic patterns
        print("\nPattern analysis:")
        if 'charset="UTF-8""' in line4:
            print("  Found: charset=\"UTF-8\"\" (double quote at end)")
        elif 'charset="UTF-8"' in line4:
            print("  Found: charset=\"UTF-8\" (normal)")
        else:
            print("  No charset pattern found")
        
        # Look for the exact error position
        print(f"\nCharacter at column 70 (if exists):")
        if len(line4) >= 70:
            char70 = line4[69]  # 0-indexed
            print(f"  Character: '{char70}' (ASCII: {ord(char70)})")
            
            # Show context around it
            start_ctx = max(0, 65)
            end_ctx = min(len(line4), 75)
            context = line4[start_ctx:end_ctx]
            print(f"  Context (pos 66-75): '{context}'")

def main():
    files_to_check = [
        'temp_debug/titlepage.xhtml',
        'temp_debug/OEBPS/cover.xhtml'
    ]
    
    for filepath in files_to_check:
        if os.path.exists(filepath):
            analyze_file(filepath)
            print("\n" + "="*50 + "\n")
        else:
            print(f"File not found: {filepath}")

if __name__ == '__main__':
    main()