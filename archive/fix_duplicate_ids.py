#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix duplicate fragment identifiers in EPUB chapter files.
The issue is that each chapter has duplicate ID attributes like 'sec1', 'sec2', etc.
appearing multiple times within the same file, which violates HTML standards.
"""

import os
import zipfile
import re
from pathlib import Path
import subprocess
import tempfile
import shutil

def extract_epub(epub_path, extract_dir):
    """Extract EPUB file to directory"""
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print(f"Extracted EPUB to: {extract_dir}")

def fix_duplicate_ids_in_file(file_path, chapter_num):
    """Fix duplicate IDs in a single XHTML file by making them unique"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    fixes_applied = 0
    
    # Pattern to find span elements with id attributes like sec1, sec2, etc.
    # First, handle the line with multiple spans (like line 18)
    multiple_spans_pattern = r'(<h1[^>]*>)(<span id="sec\d+"></span>)+'
    
    def replace_multiple_spans(match):
        nonlocal fixes_applied
        h1_start = match.group(1)
        # Remove all the span elements from the h1 tag
        fixes_applied += 1
        return h1_start
    
    content = re.sub(multiple_spans_pattern, replace_multiple_spans, content)
    
    # Now handle individual section headers with duplicate IDs
    # Pattern to find h2, h3 elements with id="secX" where X is a number
    section_pattern = r'(<h[23][^>]*\s+id=")(sec\d+)("[^>]*>)'
    
    def replace_section_id(match):
        nonlocal fixes_applied
        prefix = match.group(1)
        old_id = match.group(2)
        suffix = match.group(3)
        # Make ID unique by adding chapter number
        new_id = f"ch{chapter_num:02d}_{old_id}"
        fixes_applied += 1
        return f"{prefix}{new_id}{suffix}"
    
    content = re.sub(section_pattern, replace_section_id, content)
    
    # Also fix any anchor links that reference these IDs
    anchor_pattern = r'(<a[^>]*href="#)(sec\d+)("[^>]*>)'
    
    def replace_anchor_href(match):
        nonlocal fixes_applied
        prefix = match.group(1)
        old_id = match.group(2)
        suffix = match.group(3)
        # Update href to match new ID format
        new_id = f"ch{chapter_num:02d}_{old_id}"
        fixes_applied += 1
        return f"{prefix}{new_id}{suffix}"
    
    content = re.sub(anchor_pattern, replace_anchor_href, content)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {fixes_applied} duplicate IDs in {os.path.basename(file_path)}")
        return fixes_applied
    else:
        print(f"No duplicate IDs found in {os.path.basename(file_path)}")
        return 0

def repack_epub(extract_dir, output_path):
    """Repack directory into EPUB file"""
    if os.path.exists(output_path):
        os.remove(output_path)
    
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
    
    print(f"Repacked EPUB to: {output_path}")

def run_epubcheck(epub_path, output_file):
    """Run epubcheck validation"""
    jar_path = "epubcheck.jar"
    if not os.path.exists(jar_path):
        print(f"Error: {jar_path} not found")
        return False
    
    try:
        result = subprocess.run(
            ["java", "-jar", jar_path, epub_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Validating using EPUB version 2.0.1 rules.\n")
            f.write(f"Return code: {result.returncode}\n\n")
            f.write("--- STDOUT ---\n")
            f.write(result.stdout)
            f.write("\n--- STDERR ---\n")
            f.write(result.stderr)
        
        print(f"Validation results saved to: {output_file}")
        return True
        
    except subprocess.TimeoutExpired:
        print("Epubcheck timed out")
        return False
    except Exception as e:
        print(f"Error running epubcheck: {e}")
        return False

def main():
    epub_file = "doing2_comprehensive_fixed.epub"
    extract_dir = "duplicate_ids_debug"
    output_epub = "doing2_ids_fixed.epub"
    validation_file = "duplicate_ids_validation.txt"
    
    if not os.path.exists(epub_file):
        print(f"Error: {epub_file} not found")
        return
    
    # Extract EPUB
    extract_epub(epub_file, extract_dir)
    
    # Fix duplicate IDs in all chapter files
    oebps_dir = os.path.join(extract_dir, "OEBPS")
    total_fixes = 0
    
    # Process chapter files
    for i in range(1, 11):  # chapters 01-10
        chapter_file = os.path.join(oebps_dir, f"chapter{i:02d}.xhtml")
        if os.path.exists(chapter_file):
            fixes = fix_duplicate_ids_in_file(chapter_file, i)
            total_fixes += fixes
    
    print(f"\nTotal fixes applied: {total_fixes}")
    
    # Repack EPUB
    repack_epub(extract_dir, output_epub)
    
    # Run validation
    print("\nRunning epubcheck validation...")
    run_epubcheck(output_epub, validation_file)
    
    print(f"\nProcess completed. Check {validation_file} for results.")

if __name__ == "__main__":
    main()