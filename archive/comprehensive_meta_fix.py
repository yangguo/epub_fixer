#!/usr/bin/env python3
"""
Comprehensive Meta Tag Fix for EPUB
Fixes malformed charset attributes in all XHTML files
"""

import os
import zipfile
import tempfile
import shutil
import subprocess
import re
from pathlib import Path

def extract_epub(epub_path, extract_dir):
    """Extract EPUB to directory"""
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print(f"Extracted EPUB to: {extract_dir}")

def fix_meta_charset(content):
    """Fix malformed charset attributes in meta tags"""
    fixes_applied = 0
    
    # Pattern 1: charset=""UTF-8" -> charset=UTF-8
    pattern1 = r'charset=""UTF-8"'
    if re.search(pattern1, content):
        content = re.sub(pattern1, 'charset=UTF-8', content)
        fixes_applied += 1
        print(f"  Fixed pattern: charset=\"\"UTF-8\"")
    
    # Pattern 2: charset=""utf-8" -> charset=utf-8
    pattern2 = r'charset=""utf-8"'
    if re.search(pattern2, content):
        content = re.sub(pattern2, 'charset=utf-8', content)
        fixes_applied += 1
        print(f"  Fixed pattern: charset=\"\"utf-8\"")
    
    # Pattern 3: Fix the specific malformed pattern in content attribute
    # content="text/html; charset="UTF-8" -> content="text/html; charset=UTF-8"
    pattern3 = r'content="([^"]*);\s*charset="UTF-8"'
    if re.search(pattern3, content):
        content = re.sub(pattern3, r'content="\1; charset=UTF-8"', content)
        fixes_applied += 1
        print(f"  Fixed pattern: content with charset=\"UTF-8\"")
    
    # Pattern 4: Fix the specific malformed pattern in content attribute (lowercase)
    # content="text/html; charset="utf-8" -> content="text/html; charset=utf-8"
    pattern4 = r'content="([^"]*);\s*charset="utf-8"'
    if re.search(pattern4, content):
        content = re.sub(pattern4, r'content="\1; charset=utf-8"', content)
        fixes_applied += 1
        print(f"  Fixed pattern: content with charset=\"utf-8\"")
    
    return content, fixes_applied

def process_xhtml_files(extract_dir):
    """Process all XHTML files in the extracted EPUB"""
    total_fixes = 0
    
    # Find all XHTML files
    xhtml_files = []
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith('.xhtml') or file.endswith('.html'):
                xhtml_files.append(os.path.join(root, file))
    
    print(f"Found {len(xhtml_files)} XHTML files to process")
    
    for xhtml_file in xhtml_files:
        print(f"Processing: {os.path.relpath(xhtml_file, extract_dir)}")
        
        # Read file
        try:
            with open(xhtml_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(xhtml_file, 'r', encoding='latin-1') as f:
                content = f.read()
        
        # Fix meta tags
        new_content, fixes = fix_meta_charset(content)
        total_fixes += fixes
        
        # Write back if changes were made
        if fixes > 0:
            with open(xhtml_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  Applied {fixes} fixes")
        else:
            print(f"  No fixes needed")
    
    return total_fixes

def repack_epub(extract_dir, output_path):
    """Repack directory into EPUB"""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        # Add mimetype first (uncompressed)
        mimetype_path = os.path.join(extract_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            zip_ref.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == 'mimetype':
                    continue  # Already added
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, extract_dir)
                zip_ref.write(file_path, arc_path)
    
    print(f"Repacked EPUB: {output_path}")

def run_epubcheck(epub_path, output_file):
    """Run epubcheck validation"""
    try:
        result = subprocess.run(
            ['java', '-jar', 'epubcheck.jar', epub_path],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        # Write validation results
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n--- STDERR ---\n")
                f.write(result.stderr)
        
        print(f"Validation results saved to: {output_file}")
        
        # Parse results
        if result.stderr:
            lines = result.stderr.split('\n')
            fatal_count = len([line for line in lines if 'FATAL' in line])
            error_count = len([line for line in lines if 'ERROR' in line and 'FATAL' not in line])
            print(f"Validation: {fatal_count} fatal errors, {error_count} regular errors")
        
        return result.returncode == 0
        
    except FileNotFoundError:
        print("Error: epubcheck.jar not found")
        return False
    except Exception as e:
        print(f"Error running epubcheck: {e}")
        return False

def main():
    # File paths
    input_epub = "doing2.epub"
    output_epub = "doing2_comprehensive_fixed.epub"
    debug_dir = "comprehensive_debug"
    validation_file = "comprehensive_validation.txt"
    
    print("=== Comprehensive Meta Tag Fix (Corrected) ===")
    print(f"Input: {input_epub}")
    print(f"Output: {output_epub}")
    
    # Clean up previous debug directory
    if os.path.exists(debug_dir):
        shutil.rmtree(debug_dir)
    
    try:
        # Extract EPUB
        extract_epub(input_epub, debug_dir)
        
        # Process XHTML files
        total_fixes = process_xhtml_files(debug_dir)
        print(f"\nTotal fixes applied: {total_fixes}")
        
        # Repack EPUB
        repack_epub(debug_dir, output_epub)
        
        # Validate
        print("\nRunning validation...")
        run_epubcheck(output_epub, validation_file)
        
        print("\n=== Process Complete ===")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())