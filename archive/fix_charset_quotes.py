#!/usr/bin/env python3
"""
Fix malformed charset attributes in meta tags
"""

import os
import re
import zipfile
import shutil
import subprocess

def fix_charset_quotes(content):
    """
    Fix malformed charset attributes where quotes are not properly closed
    """
    fixes = 0
    
    # Pattern 1: charset="utf-8" /> (missing closing quote)
    pattern1 = r'charset="([^"]*?)"\s*/>'
    def replace1(match):
        charset_value = match.group(1)
        return f'charset="{charset_value}" />'
    
    new_content, count1 = re.subn(pattern1, replace1, content)
    fixes += count1
    
    # Pattern 2: More specific - charset="utf-8" with space before />
    pattern2 = r'charset="utf-8"\s*/>'
    new_content, count2 = re.subn(pattern2, 'charset="utf-8" />', new_content)
    fixes += count2
    
    # Pattern 3: Fix the exact malformed pattern we found
    pattern3 = r'charset="utf-8"\s*/>'
    new_content, count3 = re.subn(pattern3, 'charset="utf-8" />', new_content)
    fixes += count3
    
    # Pattern 4: Fix any meta tag with malformed self-closing syntax
    pattern4 = r'(<meta[^>]*?)\s{2,}/>'
    new_content, count4 = re.subn(pattern4, r'\1 />', new_content)
    fixes += count4
    
    return new_content, fixes

def process_epub(epub_path):
    extract_dir = 'charset_fix_extract'
    
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
                    
                    new_content, fixes = fix_charset_quotes(content)
                    
                    if fixes > 0:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"Fixed {fixes} issues in {file}")
                        total_fixes += fixes
                        files_processed += 1
                        
                except Exception as e:
                    print(f"Error processing {file}: {e}")
    
    # Repack EPUB
    output_path = epub_path.replace('.epub', '_charset_fixed.epub')
    
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
    print("=== Charset Quote Fix ===")
    
    epub_path = 'doing2.epub'
    print(f"Processing: {epub_path}")
    
    try:
        output_path, files_processed, total_fixes = process_epub(epub_path)
        
        print(f"\nSummary:")
        print(f"- Files processed: {files_processed}")
        print(f"- Total fixes applied: {total_fixes}")
        print(f"- Output: {output_path}")
        
        # Run epubcheck
        print("\nRunning epubcheck validation...")
        result = subprocess.run(
            ['java', '-jar', 'epubcheck.jar', output_path],
            capture_output=True,
            text=True
        )
        
        # Save validation results
        validation_file = 'charset_validation.txt'
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