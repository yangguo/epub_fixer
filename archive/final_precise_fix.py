#!/usr/bin/env python3
import zipfile
import os
import re
from pathlib import Path

def fix_final_meta_issues():
    """Fix the exact meta tag issues with precise pattern matching"""
    
    # Extract EPUB
    with zipfile.ZipFile('doing1.epub', 'r') as zip_ref:
        zip_ref.extractall('final_temp')
    
    fixed_files = []
    
    # Process all XHTML files in OEBPS
    oebps_dir = Path('final_temp/OEBPS')
    for file_path in oebps_dir.glob('*.xhtml'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix the exact charset issue: charset="utf-8" -> charset="utf-8"
            # This targets the literal quote character at the end
            content = content.replace('charset="utf-8"', 'charset="utf-8"')
            content = content.replace('charset="UTF-8"', 'charset="UTF-8"')
            
            # More comprehensive fix for any charset with extra quote
            content = re.sub(r'charset="([^"]+)""', r'charset="\1"', content)
            
            # Fix any remaining quote issues in meta tags
            content = re.sub(r'content="([^"]*?)""', r'content="\1"', content)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_files.append(file_path.name)
                print(f"Fixed: {file_path.name}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Also check titlepage.xhtml in root
    titlepage_path = Path('final_temp/titlepage.xhtml')
    if titlepage_path.exists():
        try:
            with open(titlepage_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            content = content.replace('charset="utf-8"', 'charset="utf-8"')
            content = content.replace('charset="UTF-8"', 'charset="UTF-8"')
            content = re.sub(r'charset="([^"]+)""', r'charset="\1"', content)
            content = re.sub(r'content="([^"]*?)""', r'content="\1"', content)
            
            if content != original_content:
                with open(titlepage_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_files.append('titlepage.xhtml')
                print(f"Fixed: titlepage.xhtml")
                
        except Exception as e:
            print(f"Error processing titlepage.xhtml: {e}")
    
    # Repack EPUB with proper mimetype ordering
    with zipfile.ZipFile('doing1.epub', 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        # Add mimetype first (uncompressed)
        mimetype_path = Path('final_temp/mimetype')
        if mimetype_path.exists():
            zip_ref.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk('final_temp'):
            for file in files:
                if file == 'mimetype':
                    continue
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, 'final_temp')
                zip_ref.write(file_path, arc_name)
    
    # Clean up
    import shutil
    shutil.rmtree('final_temp')
    
    print(f"\nFixed {len(fixed_files)} files: {', '.join(fixed_files)}")
    print("EPUB repacked successfully.")

if __name__ == "__main__":
    fix_final_meta_issues()