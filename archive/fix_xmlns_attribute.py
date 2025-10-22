#!/usr/bin/env python3
"""
Fix malformed xmlns attributes in HTML files within EPUB
"""

import zipfile
import os
import re
import subprocess
from pathlib import Path

def fix_xmlns_attributes():
    epub_path = "future1.epub"
    extract_dir = "epub_temp"
    
    print("Extracting EPUB...")
    # Extract EPUB
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # Find all HTML files
    html_files = []
    text_dir = os.path.join(extract_dir, "text")
    if os.path.exists(text_dir):
        for file in os.listdir(text_dir):
            if file.endswith(".html"):
                html_files.append(os.path.join(text_dir, file))
    
    # Also check for titlepage.xhtml
    titlepage_path = os.path.join(extract_dir, "titlepage.xhtml")
    if os.path.exists(titlepage_path):
        html_files.append(titlepage_path)
    
    print(f"Found {len(html_files)} HTML files to process")
    
    fixed_count = 0
    
    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix malformed xmlns attribute
            # Pattern: xmlns="http://www.w3.org/1999/> (missing closing quote and xhtml)
            content = re.sub(
                r'xmlns="http://www\.w3\.org/1999/>',
                'xmlns="http://www.w3.org/1999/xhtml">',
                content
            )
            
            # Also fix any other malformed xmlns patterns
            content = re.sub(
                r'xmlns="http://www\.w3\.org/1999/[^"]*"?[^>]*>',
                'xmlns="http://www.w3.org/1999/xhtml">',
                content
            )
            
            # Fix incomplete html tags
            content = re.sub(
                r'<html\s+xmlns="[^"]*"[^>]*$',
                '<html xmlns="http://www.w3.org/1999/xhtml">',
                content,
                flags=re.MULTILINE
            )
            
            if content != original_content:
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_count += 1
                print(f"Fixed: {os.path.basename(html_file)}")
        
        except Exception as e:
            print(f"Error processing {html_file}: {e}")
    
    print(f"\nFixed {fixed_count} files")
    
    # Repack EPUB
    print("\nRepacking EPUB...")
    if os.path.exists(epub_path):
        os.remove(epub_path)
    
    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, extract_dir)
                zipf.write(file_path, arcname)
    
    # Clean up
    import shutil
    shutil.rmtree(extract_dir)
    
    print("EPUB repacked successfully")
    
    # Run epubcheck
    print("\nRunning epubcheck...")
    try:
        result = subprocess.run(
            ["java", "-jar", "epubcheck.jar", epub_path],
            capture_output=True,
            text=True,
            cwd="."
        )
        
        # Save output to file
        with open("output.txt", "w", encoding="utf-8") as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n--- STDERR ---\n")
                f.write(result.stderr)
        
        print("EPUBCheck completed")
        
    except Exception as e:
        print(f"Error running epubcheck: {e}")

if __name__ == "__main__":
    fix_xmlns_attributes()