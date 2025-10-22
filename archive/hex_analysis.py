#!/usr/bin/env python3
"""
Hex analysis of problematic meta tags
"""

import os
import zipfile

def analyze_hex_content(filepath, line_num, col_num):
    """
    Analyze the hex content around the error position
    """
    with open(filepath, 'rb') as f:
        content_bytes = f.read()
    
    # Convert to string to find line
    content_str = content_bytes.decode('utf-8', errors='replace')
    lines = content_str.split('\n')
    
    if line_num <= len(lines):
        line = lines[line_num - 1]
        print(f"\nAnalyzing {filepath} at line {line_num}, column {col_num}:")
        print(f"Line content: '{line}'")
        print(f"Line length: {len(line)}")
        
        # Convert line to bytes
        line_bytes = line.encode('utf-8')
        print(f"Line bytes length: {len(line_bytes)}")
        
        # Show hex representation
        print("\nHex representation of the line:")
        for i, byte_val in enumerate(line_bytes):
            char = chr(byte_val) if 32 <= byte_val <= 126 else f'\\x{byte_val:02x}'
            marker = " <-- COL " + str(col_num) if i == col_num - 1 else ""
            print(f"  Pos {i+1:2d}: 0x{byte_val:02x} '{char}'{marker}")
        
        # Look for specific patterns around charset
        if 'charset=' in line:
            charset_pos = line.find('charset=')
            print(f"\nCharset found at position: {charset_pos + 1}")
            
            # Show context around charset
            start = max(0, charset_pos - 5)
            end = min(len(line_bytes), charset_pos + 20)
            print(f"\nHex context around charset (pos {start+1} to {end}):")
            for i in range(start, end):
                if i < len(line_bytes):
                    byte_val = line_bytes[i]
                    char = chr(byte_val) if 32 <= byte_val <= 126 else f'\\x{byte_val:02x}'
                    marker = " <-- ERROR" if i == col_num - 1 else ""
                    print(f"  Pos {i+1:2d}: 0x{byte_val:02x} '{char}'{marker}")

def extract_and_analyze():
    """
    Extract EPUB and analyze problematic files
    """
    input_epub = 'doing2_ultimate_fixed.epub'
    extract_dir = 'hex_analysis_temp'
    
    if os.path.exists(extract_dir):
        import shutil
        shutil.rmtree(extract_dir)
    
    # Extract EPUB
    with zipfile.ZipFile(input_epub, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # Analyze specific problematic files
    problem_files = [
        ('OEBPS/cover.xhtml', 6, 66),
        ('titlepage.xhtml', 4, 70),
        ('OEBPS/title.xhtml', 6, 66),
    ]
    
    for file_path, line_num, col_num in problem_files:
        full_path = os.path.join(extract_dir, file_path)
        if os.path.exists(full_path):
            analyze_hex_content(full_path, line_num, col_num)
        else:
            print(f"File not found: {full_path}")
    
    # Clean up
    import shutil
    shutil.rmtree(extract_dir)

def main():
    if not os.path.exists('doing2_ultimate_fixed.epub'):
        print("Input file doing2_ultimate_fixed.epub not found!")
        return
    
    print("Starting hex analysis...")
    extract_and_analyze()

if __name__ == '__main__':
    main()