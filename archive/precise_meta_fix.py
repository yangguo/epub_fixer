#!/usr/bin/env python3
"""
Precise meta tag fix script to address the exact malformation pattern.
Targets meta tags with double spaces before closing />.
"""

import os
import re
import zipfile
import shutil
import subprocess

def extract_epub(epub_path, extract_dir):
    """Extract EPUB file to directory"""
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir)
    
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print(f"Extracted EPUB to {extract_dir}")

def fix_meta_tags_precise(content):
    """Fix meta tags with precise pattern matching"""
    fixes_applied = 0
    original_content = content
    
    # Pattern 1: Fix meta tags with double spaces before />
    # From: name="Adept.expected.resource"  /> to: name="Adept.expected.resource" />
    pattern1 = r'(<meta[^>]+)\s\s+/>'
    matches = re.findall(pattern1, content)
    if matches:
        content = re.sub(pattern1, r'\1 />', content)
        fixes_applied += len(matches)
        print(f"Fixed {len(matches)} meta tags with double spaces")
    
    # Pattern 2: Fix any meta tag with multiple spaces before />
    pattern2 = r'(<meta[^>]+)\s{2,}/>'
    matches = re.findall(pattern2, content)
    if matches:
        content = re.sub(pattern2, r'\1 />', content)
        fixes_applied += len(matches)
        print(f"Fixed {len(matches)} meta tags with multiple spaces")
    
    # Pattern 3: Fix img tags with double spaces before />
    pattern3 = r'(<img[^>]+)\s\s+/>'
    matches = re.findall(pattern3, content)
    if matches:
        content = re.sub(pattern3, r'\1 />', content)
        fixes_applied += len(matches)
        print(f"Fixed {len(matches)} img tags with double spaces")
    
    # Pattern 4: Fix any self-closing tag with multiple spaces before />
    pattern4 = r'(<(?:meta|img|link|br|hr|input)[^>]+)\s{2,}/>'
    matches = re.findall(pattern4, content)
    if matches:
        content = re.sub(pattern4, r'\1 />', content)
        fixes_applied += len(matches)
        print(f"Fixed {len(matches)} self-closing tags with multiple spaces")
    
    if content != original_content:
        print(f"Content changed, {fixes_applied} total fixes applied")
    
    return content, fixes_applied

def process_xhtml_files(extract_dir):
    """Process all XHTML files in the extracted EPUB"""
    total_fixes = 0
    processed_files = []
    
    # Process files in OEBPS directory
    oebps_dir = os.path.join(extract_dir, 'OEBPS')
    if os.path.exists(oebps_dir):
        for filename in os.listdir(oebps_dir):
            if filename.endswith('.xhtml') or filename.endswith('.html'):
                filepath = os.path.join(oebps_dir, filename)
                fixes = process_single_file(filepath, filename)
                if fixes > 0:
                    processed_files.append(filename)
                    total_fixes += fixes
    
    # Process files in root directory
    for filename in os.listdir(extract_dir):
        if filename.endswith('.xhtml') or filename.endswith('.html'):
            filepath = os.path.join(extract_dir, filename)
            fixes = process_single_file(filepath, filename)
            if fixes > 0:
                processed_files.append(filename)
                total_fixes += fixes
    
    return len(processed_files), total_fixes

def process_single_file(filepath, filename):
    """Process a single XHTML file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        content, fixes = fix_meta_tags_precise(content)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed {filename}: {fixes} fixes applied")
            return fixes
        
        return 0
        
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return 0

def repack_epub(extract_dir, output_path):
    """Repack the EPUB with proper structure"""
    if os.path.exists(output_path):
        os.remove(output_path)
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add mimetype first (uncompressed)
        mimetype_path = os.path.join(extract_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            zipf.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == 'mimetype':
                    continue
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, extract_dir)
                zipf.write(file_path, arc_path)
    
    print(f"Repacked EPUB as {output_path}")

def run_epubcheck(epub_path):
    """Run epubcheck and return the results"""
    try:
        result = subprocess.run(
            ['java', '-jar', 'epubcheck.jar', epub_path],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error running epubcheck: {e}"

def main():
    epub_file = 'doing2.epub'
    extract_dir = 'precise_fix_extract'
    output_file = 'doing2_precise_fixed.epub'
    
    print("=== Precise Meta Tag Fix ===")
    print(f"Processing: {epub_file}")
    
    # Extract EPUB
    extract_epub(epub_file, extract_dir)
    
    # Process XHTML files
    print("\nProcessing XHTML files...")
    files_processed, total_fixes = process_xhtml_files(extract_dir)
    
    print(f"\nSummary:")
    print(f"- Files processed: {files_processed}")
    print(f"- Total fixes applied: {total_fixes}")
    
    # Repack EPUB
    print("\nRepacking EPUB...")
    repack_epub(extract_dir, output_file)
    
    # Run epubcheck
    print("\nRunning epubcheck validation...")
    validation_result = run_epubcheck(output_file)
    
    # Save validation results
    with open('precise_validation.txt', 'w', encoding='utf-8') as f:
        f.write(validation_result)
    
    print("\nValidation complete. Results saved to precise_validation.txt")
    
    # Count errors
    fatal_errors = validation_result.count('FATAL(')
    regular_errors = validation_result.count('ERROR(')
    print(f"\nValidation Results:")
    print(f"- Fatal errors: {fatal_errors}")
    print(f"- Regular errors: {regular_errors}")
    
    if fatal_errors == 0 and regular_errors == 0:
        print("\n🎉 SUCCESS: EPUB is now valid!")
    elif fatal_errors == 0:
        print(f"\n✅ Fatal errors fixed! Only {regular_errors} regular errors remain")
    else:
        print(f"\n⚠️  Still has {fatal_errors} fatal and {regular_errors} regular errors")
    
    # Cleanup
    shutil.rmtree(extract_dir)
    print(f"\nCleaned up temporary directory: {extract_dir}")

if __name__ == '__main__':
    main()