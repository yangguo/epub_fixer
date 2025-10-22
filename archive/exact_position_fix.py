#!/usr/bin/env python3
"""
Exact position analysis and fix for meta tag errors
"""

import os
import re
import zipfile
import subprocess
from pathlib import Path

def analyze_exact_position(filepath, line_num, col_num):
    """
    Analyze the exact character at the given position
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if line_num <= len(lines):
        line = lines[line_num - 1]  # Convert to 0-indexed
        print(f"\nAnalyzing {filepath} at line {line_num}, column {col_num}:")
        print(f"Line content: '{line.rstrip()}'")
        print(f"Line length: {len(line.rstrip())}")
        
        if col_num <= len(line):
            char_at_pos = line[col_num - 1]  # Convert to 0-indexed
            print(f"Character at column {col_num}: '{char_at_pos}' (ASCII: {ord(char_at_pos)})")
            
            # Show context around the position
            start = max(0, col_num - 10)
            end = min(len(line), col_num + 10)
            context = line[start:end]
            print(f"Context: '{context.rstrip()}'")
            
            # Show each character in the context
            print("Character breakdown:")
            for i in range(start, end):
                if i < len(line):
                    char = line[i]
                    marker = " <-- ERROR POS" if i == col_num - 1 else ""
                    print(f"  Pos {i+1:2d}: '{char}' (ASCII: {ord(char):3d}){marker}")
        else:
            print(f"Column {col_num} is beyond line length")
    else:
        print(f"Line {line_num} not found in file")

def fix_meta_tag_at_position(content, line_num, col_num):
    """
    Fix meta tag at specific position
    """
    lines = content.split('\n')
    
    if line_num <= len(lines):
        line = lines[line_num - 1]  # Convert to 0-indexed
        
        # Check if this is a meta tag line
        if '<meta' in line:
            # Try different fixes based on common issues
            original_line = line
            
            # Fix 1: Ensure proper spacing before />
            line = re.sub(r'(charset="[^"]+")\s*/>', r'\1 />', line)
            
            # Fix 2: Fix any malformed self-closing tags
            line = re.sub(r'<meta([^>]*?)>', lambda m: f'<meta{m.group(1).rstrip()} />', line)
            
            # Fix 3: Ensure meta tags are properly self-closed
            if '<meta' in line and not line.strip().endswith('/>'):
                # Find the end of the meta tag and ensure it's self-closed
                meta_match = re.search(r'<meta[^>]*', line)
                if meta_match:
                    meta_content = meta_match.group(0)
                    if not meta_content.endswith('/'):
                        line = line.replace(meta_content, meta_content + ' /')
            
            # Fix 4: Handle specific charset issues
            line = re.sub(r'charset="UTF-8"\s*>', 'charset="UTF-8" />', line)
            line = re.sub(r'charset="utf-8"\s*>', 'charset="utf-8" />', line)
            
            if line != original_line:
                lines[line_num - 1] = line
                print(f"Fixed line {line_num}: '{original_line.strip()}' -> '{line.strip()}'")
                return '\n'.join(lines), 1
    
    return content, 0

def process_epub_with_exact_fixes(input_path, output_path):
    """
    Process EPUB with exact position fixes
    """
    total_fixes = 0
    
    # Extract EPUB
    extract_dir = 'exact_fix_temp'
    if os.path.exists(extract_dir):
        import shutil
        shutil.rmtree(extract_dir)
    
    with zipfile.ZipFile(input_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # Define the problematic files and positions from the error log
    problem_files = [
        ('titlepage.xhtml', 4, 70),
        ('OEBPS/cover.xhtml', 6, 66),
        ('OEBPS/halftitle.xhtml', 6, 66),
        ('OEBPS/title.xhtml', 6, 66),
        ('OEBPS/copyright.xhtml', 6, 66),
        ('OEBPS/toc.xhtml', 6, 66),
        ('OEBPS/illustrations.xhtml', 6, 66),
        ('OEBPS/foreword.xhtml', 6, 66),
        ('OEBPS/part01.xhtml', 6, 66),
        ('OEBPS/chapter01.xhtml', 6, 66),
        ('OEBPS/chapter02.xhtml', 6, 66),
        ('OEBPS/chapter03.xhtml', 6, 66),
        ('OEBPS/chapter04.xhtml', 6, 66),
        ('OEBPS/chapter05.xhtml', 6, 66),
        ('OEBPS/part02.xhtml', 6, 66),
        ('OEBPS/chapter06.xhtml', 6, 66),
        ('OEBPS/chapter07.xhtml', 6, 66),
        ('OEBPS/chapter08.xhtml', 6, 66),
        ('OEBPS/chapter09.xhtml', 6, 66),
        ('OEBPS/chapter10.xhtml', 6, 66),
        ('OEBPS/bib.xhtml', 6, 66),
        ('OEBPS/index.xhtml', 6, 66),
        ('OEBPS/back.xhtml', 6, 66),
    ]
    
    for file_path, line_num, col_num in problem_files:
        full_path = os.path.join(extract_dir, file_path)
        
        if os.path.exists(full_path):
            # Analyze the exact position first
            analyze_exact_position(full_path, line_num, col_num)
            
            # Read and fix the file
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                fixed_content, fixes = fix_meta_tag_at_position(content, line_num, col_num)
                
                if fixes > 0:
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)
                    total_fixes += fixes
                
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
        else:
            print(f"File not found: {full_path}")
    
    # Repack EPUB
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
        # Add mimetype first (uncompressed)
        mimetype_path = os.path.join(extract_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            zip_out.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == 'mimetype':
                    continue
                
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, extract_dir)
                zip_out.write(file_path, arcname)
    
    # Clean up
    import shutil
    shutil.rmtree(extract_dir)
    
    return total_fixes

def run_epubcheck(epub_path):
    """
    Run epubcheck and return results
    """
    try:
        result = subprocess.run(
            ['java', '-jar', 'epubcheck.jar', epub_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        output = result.stdout + result.stderr
        
        # Count errors
        fatal_errors = output.count('FATAL')
        errors = output.count('ERROR') - fatal_errors
        
        return output, fatal_errors, errors
    
    except Exception as e:
        return f"Error running epubcheck: {e}", 0, 0

def main():
    input_epub = 'doing2_ultimate_fixed.epub'
    output_epub = 'doing2_exact_fixed.epub'
    validation_file = 'exact_validation.txt'
    
    if not os.path.exists(input_epub):
        print(f"Input file {input_epub} not found!")
        return
    
    print("Starting exact position fix...")
    
    # Process the EPUB
    fixes_applied = process_epub_with_exact_fixes(input_epub, output_epub)
    
    print(f"\nApplied {fixes_applied} fixes. Running validation...")
    
    # Validate the result
    validation_output, fatal_errors, errors = run_epubcheck(output_epub)
    
    # Save validation results
    with open(validation_file, 'w', encoding='utf-8') as f:
        f.write(validation_output)
    
    print(f"\nValidation complete:")
    print(f"Fatal errors: {fatal_errors}")
    print(f"Regular errors: {errors}")
    print(f"Results saved to {validation_file}")
    
    if fatal_errors == 0 and errors == 0:
        print("\n🎉 EPUB is now valid!")
    else:
        print(f"\n⚠️  Still has {fatal_errors} fatal errors and {errors} regular errors")

if __name__ == '__main__':
    main()