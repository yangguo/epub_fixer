#!/usr/bin/env python3

import zipfile
import os
import re
import subprocess
import tempfile
import shutil

def extract_epub(epub_path, extract_dir):
    """Extract EPUB contents to a directory"""
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

def fix_toc_references(content, file_type):
    """Fix fragment identifier references in TOC files"""
    fixes_applied = 0
    
    if file_type == 'xhtml':
        # Pattern for XHTML TOC: href="chapter01.xhtml#sec1" -> href="chapter01.xhtml#ch01_sec1"
        pattern = r'href="(chapter(\d+)\.xhtml)#(sec\d+)"'
        def replacement(match):
            nonlocal fixes_applied
            fixes_applied += 1
            chapter_file = match.group(1)
            chapter_num = match.group(2).zfill(2)  # Ensure 2-digit format
            sec_id = match.group(3)
            return f'href="{chapter_file}#ch{chapter_num}_{sec_id}"'
        
        content = re.sub(pattern, replacement, content)
        
    elif file_type == 'ncx':
        # Pattern for NCX TOC: src="OEBPS/chapter01.xhtml#sec1" -> src="OEBPS/chapter01.xhtml#ch01_sec1"
        pattern = r'src="(OEBPS/chapter(\d+)\.xhtml)#(sec\d+)"'
        def replacement(match):
            nonlocal fixes_applied
            fixes_applied += 1
            chapter_file = match.group(1)
            chapter_num = match.group(2).zfill(2)  # Ensure 2-digit format
            sec_id = match.group(3)
            return f'src="{chapter_file}#ch{chapter_num}_{sec_id}"'
        
        content = re.sub(pattern, replacement, content)
    
    return content, fixes_applied

def repack_epub(extract_dir, output_path):
    """Repack the EPUB from extracted directory"""
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

def run_epubcheck(epub_path, output_file):
    """Run epubcheck validation and save results"""
    try:
        result = subprocess.run(
            ['java', '-jar', 'epubcheck.jar', epub_path],
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
        
        print(f"Validation results saved to {output_file}")
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("EPUBCheck timed out")
        return False
    except Exception as e:
        print(f"Error running EPUBCheck: {e}")
        return False

def main():
    input_epub = 'doing2_ids_fixed.epub'
    output_epub = 'doing2_toc_fixed.epub'
    validation_output = 'toc_fixed_validation.txt'
    
    if not os.path.exists(input_epub):
        print(f"Error: {input_epub} not found")
        return
    
    # Create temporary directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Extracting {input_epub}...")
        extract_epub(input_epub, temp_dir)
        
        total_fixes = 0
        
        # Fix toc.xhtml
        toc_xhtml_path = os.path.join(temp_dir, 'OEBPS', 'toc.xhtml')
        if os.path.exists(toc_xhtml_path):
            with open(toc_xhtml_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            fixed_content, fixes = fix_toc_references(content, 'xhtml')
            
            with open(toc_xhtml_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            print(f"Fixed {fixes} references in toc.xhtml")
            total_fixes += fixes
        
        # Fix toc.ncx
        toc_ncx_path = os.path.join(temp_dir, 'toc.ncx')
        if os.path.exists(toc_ncx_path):
            with open(toc_ncx_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            fixed_content, fixes = fix_toc_references(content, 'ncx')
            
            with open(toc_ncx_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            print(f"Fixed {fixes} references in toc.ncx")
            total_fixes += fixes
        
        print(f"\nTotal fixes applied: {total_fixes}")
        
        # Repack EPUB
        print(f"Repacking to {output_epub}...")
        repack_epub(temp_dir, output_epub)
        
        # Validate
        print("Running EPUBCheck validation...")
        run_epubcheck(output_epub, validation_output)
        
        print(f"\nProcess completed!")
        print(f"Fixed EPUB: {output_epub}")
        print(f"Validation report: {validation_output}")

if __name__ == '__main__':
    main()