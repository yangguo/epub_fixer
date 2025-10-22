#!/usr/bin/env python3
"""
Fix malformed meta tag syntax - specifically the charset quote issue
"""

import os
import re
import zipfile
import shutil
import subprocess

def fix_meta_syntax(content):
    """
    Fix malformed meta tag syntax
    The issue is charset="utf-8"" (extra quote at the end)
    """
    fixes = 0
    original_content = content
    
    # Pattern 1: Fix charset="utf-8"" (extra quote) to charset="utf-8"
    pattern1 = r'charset="utf-8""'
    new_content, count1 = re.subn(pattern1, 'charset="utf-8"', content)
    fixes += count1
    if count1 > 0:
        print(f"    Fixed {count1} charset double-quote issues")
    
    # Pattern 2: Fix charset="UTF-8"" (extra quote) to charset="UTF-8"
    pattern2 = r'charset="UTF-8""'
    new_content, count2 = re.subn(pattern2, 'charset="UTF-8"', new_content)
    fixes += count2
    if count2 > 0:
        print(f"    Fixed {count2} charset double-quote issues (uppercase)")
    
    # Pattern 3: Fix any charset with double quotes
    pattern3 = r'charset="([^"]+)""'
    new_content, count3 = re.subn(pattern3, r'charset="\1"', new_content)
    fixes += count3
    if count3 > 0:
        print(f"    Fixed {count3} general charset double-quote issues")
    
    # Pattern 4: Fix extra spaces before /> in meta tags
    pattern4 = r'(<meta[^>]*?)\s{2,}/>'
    new_content, count4 = re.subn(pattern4, r'\1 />', new_content)
    fixes += count4
    if count4 > 0:
        print(f"    Fixed {count4} meta tag spacing issues")
    
    # Pattern 5: Fix empty alt attributes
    pattern5 = r'alt=""'
    new_content, count5 = re.subn(pattern5, 'alt="Cover image"', new_content)
    fixes += count5
    if count5 > 0:
        print(f"    Fixed {count5} empty alt attributes")
    
    return new_content, fixes

def process_epub(epub_path):
    extract_dir = 'meta_syntax_extract'
    
    # Clean up any existing extract directory
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    
    # Extract EPUB
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    total_fixes = 0
    files_processed = 0
    
    # Process all XHTML files
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith(('.xhtml', '.html')):
                filepath = os.path.join(root, file)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content, fixes = fix_meta_syntax(content)
                    
                    if fixes > 0:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"Fixed {fixes} issues in {file}")
                        total_fixes += fixes
                        files_processed += 1
                        
                        # Show the fixed lines for key files
                        if 'cover.xhtml' in file:
                            print(f"  Fixed content in {file}:")
                            lines = new_content.split('\n')
                            for i, line in enumerate(lines):
                                if 'meta' in line and 'charset' in line:
                                    print(f"    Line {i+1}: {line.strip()}")
                        
                except Exception as e:
                    print(f"Error processing {file}: {e}")
    
    # Repack EPUB
    output_path = epub_path.replace('.epub', '_syntax_fixed.epub')
    
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
                    
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, extract_dir)
                zip_out.write(filepath, arcname)
    
    # Clean up
    shutil.rmtree(extract_dir)
    
    return output_path, files_processed, total_fixes

def main():
    print("=== Meta Tag Syntax Fix ===")
    print("Targeting charset double-quote issue: charset=\"utf-8\"\" -> charset=\"utf-8\"")
    
    epub_path = 'doing2.epub'
    print(f"Processing: {epub_path}")
    
    try:
        output_path, files_processed, total_fixes = process_epub(epub_path)
        
        print(f"\nSummary:")
        print(f"- Files processed: {files_processed}")
        print(f"- Total fixes applied: {total_fixes}")
        print(f"- Output: {output_path}")
        
        if total_fixes == 0:
            print("\n⚠️  No fixes were applied. The issue might be different than expected.")
            return
        
        # Run epubcheck
        print("\nRunning epubcheck validation...")
        result = subprocess.run(
            ['java', '-jar', 'epubcheck.jar', output_path],
            capture_output=True,
            text=True
        )
        
        # Save validation results
        validation_file = 'syntax_validation.txt'
        with open(validation_file, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n=== STDERR ===\n")
                f.write(result.stderr)
        
        print(f"Validation complete. Results saved to {validation_file}")
        
        # Count errors
        fatal_count = result.stdout.count('FATAL(')
        error_count = result.stdout.count('ERROR(')
        
        print(f"\nValidation Results:")
        print(f"- Fatal errors: {fatal_count}")
        print(f"- Regular errors: {error_count}")
        
        if fatal_count == 0 and error_count == 0:
            print("\n✅ EPUB is now valid!")
        elif fatal_count < 23 or error_count < 76:
            print(f"\n✅ Progress made! Reduced from 23 fatal and 76 regular errors")
        else:
            print(f"\n⚠️  Still has {fatal_count} fatal and {error_count} regular errors")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()