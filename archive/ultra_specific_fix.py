#!/usr/bin/env python3
import zipfile
import os
import re
from pathlib import Path

def fix_specific_meta_issue():
    """Fix the very specific meta charset issue with extra quotes"""
    
    # Extract EPUB
    with zipfile.ZipFile('doing1.epub', 'r') as zip_ref:
        zip_ref.extractall('temp_epub_fix')
    
    # Find all XHTML files
    oebps_dir = Path('temp_epub_fix/OEBPS')
    fixed_files = []
    
    for file_path in oebps_dir.glob('*.xhtml'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix the very specific issue: charset="utf-8" -> charset="utf-8"
            content = content.replace('charset="utf-8"', 'charset="utf-8"')
            content = content.replace('charset="UTF-8"', 'charset="UTF-8"')
            
            # Also check for any other charset patterns with extra quotes
            content = re.sub(r'charset="([^"]+)""', r'charset="\1"', content)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_files.append(file_path.name)
                print(f"Fixed: {file_path.name}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Also check titlepage.xhtml in root
    titlepage_path = Path('temp_epub_fix/titlepage.xhtml')
    if titlepage_path.exists():
        try:
            with open(titlepage_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            content = content.replace('charset="utf-8"', 'charset="utf-8"')
            content = content.replace('charset="UTF-8"', 'charset="UTF-8"')
            content = re.sub(r'charset="([^"]+)""', r'charset="\1"', content)
            
            if content != original_content:
                with open(titlepage_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_files.append('titlepage.xhtml')
                print(f"Fixed: titlepage.xhtml")
                
        except Exception as e:
            print(f"Error processing titlepage.xhtml: {e}")
    
    # Repack EPUB
    with zipfile.ZipFile('doing1.epub', 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        for root, dirs, files in os.walk('temp_epub_fix'):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, 'temp_epub_fix')
                zip_ref.write(file_path, arc_name)
    
    # Clean up
    import shutil
    shutil.rmtree('temp_epub_fix')
    
    print(f"\nFixed {len(fixed_files)} files: {', '.join(fixed_files)}")
    print("EPUB repacked successfully.")

if __name__ == "__main__":
    fix_specific_meta_issue()