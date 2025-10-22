#!/usr/bin/env python3
"""
Direct fix for the specific meta tag and img tag issues in doing1.epub
"""

import os
import re
import zipfile
import shutil

def fix_meta_and_img_tags(content):
    """Fix the specific meta tag and img tag issues"""
    # Fix meta tags with space before closing /> (e.g., / />)
    content = re.sub(r'\s+/\s*/>', ' />', content)
    
    # Fix img tags with missing quote in alt attribute
    content = re.sub(r'alt="\s+src="([^"]*?)"', r'alt="" src="\1"', content)
    
    # Fix img tags with malformed closing
    content = re.sub(r'<img([^>]*?)\s+/\s*/>', r'<img\1 />', content)
    
    return content

def fix_epub_direct():
    """Directly fix the EPUB by extracting, fixing, and repacking"""
    epub_file = 'doing1.epub'
    extract_dir = 'extracted_epub'
    
    print(f"Extracting {epub_file}...")
    
    # Extract EPUB
    with zipfile.ZipFile(epub_file, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    print("Fixing files...")
    
    # Fix all XHTML files
    files_fixed = 0
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith(('.xhtml', '.html')):
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    original_content = content
                    content = fix_meta_and_img_tags(content)
                    
                    if content != original_content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        print(f"Fixed: {file}")
                        files_fixed += 1
                        
                except Exception as e:
                    print(f"Error fixing {file}: {e}")
    
    print(f"Fixed {files_fixed} files")
    
    # Repack EPUB
    print(f"Repacking {epub_file}...")
    
    if os.path.exists(epub_file):
        os.remove(epub_file)
    
    with zipfile.ZipFile(epub_file, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        # Add mimetype first (uncompressed)
        mimetype_path = os.path.join(extract_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            zip_ref.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file != 'mimetype':  # Skip mimetype as it's already added
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, extract_dir)
                    zip_ref.write(file_path, arc_path)
    
    print(f"Repacked {epub_file}")
    
    # Clean up
    shutil.rmtree(extract_dir)
    print("Cleanup completed")

if __name__ == '__main__':
    fix_epub_direct()