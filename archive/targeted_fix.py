#!/usr/bin/env python3
import zipfile
import os
import re
from pathlib import Path

def fix_meta_charset_issue():
    """Fix the specific meta charset issue in EPUB files"""
    
    # Extract EPUB
    with zipfile.ZipFile('doing1.epub', 'r') as zip_ref:
        zip_ref.extractall('temp_epub')
    
    # Find all XHTML files
    oebps_dir = Path('temp_epub/OEBPS')
    fixed_files = []
    
    for file_path in oebps_dir.glob('*.xhtml'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix the specific charset issue: charset="utf-8" -> charset="utf-8"
            content = re.sub(r'charset="([^"]+)"\s*/', r'charset="\1"/', content)
            
            # Fix any remaining space before /> in meta tags
            content = re.sub(r'(<meta[^>]+)\s+/>', r'\1/>', content)
            
            # Fix malformed img tags
            content = re.sub(r'<img\s+alt=""?\s+src=', r'<img alt="" src=', content)
            content = re.sub(r'(<img[^>]+)\s+/>', r'\1/>', content)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_files.append(file_path.name)
                print(f"Fixed: {file_path.name}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Repack EPUB
    with zipfile.ZipFile('doing1.epub', 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        for root, dirs, files in os.walk('temp_epub'):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, 'temp_epub')
                zip_ref.write(file_path, arc_name)
    
    # Clean up
    import shutil
    shutil.rmtree('temp_epub')
    
    print(f"\nFixed {len(fixed_files)} files: {', '.join(fixed_files)}")
    print("EPUB repacked successfully.")

if __name__ == "__main__":
    fix_meta_charset_issue()