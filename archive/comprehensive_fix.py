#!/usr/bin/env python3
import zipfile
import os
import re
from pathlib import Path

def fix_all_meta_issues():
    """Fix all meta tag issues comprehensively"""
    
    # Extract EPUB
    with zipfile.ZipFile('doing1.epub', 'r') as zip_ref:
        zip_ref.extractall('comp_temp')
    
    fixed_files = []
    
    # Process all XHTML files in OEBPS
    oebps_dir = Path('comp_temp/OEBPS')
    for file_path in oebps_dir.glob('*.xhtml'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix charset issues with regex - handle all quote variations
            content = re.sub(r'charset="([^"]+)""', r'charset="\1"', content)
            content = re.sub(r'charset="([^"]+)"([^>]*?)"', r'charset="\1"\2', content)
            
            # Fix space before self-closing tags
            content = re.sub(r'\s+/\s*>', '/>', content)
            
            # Fix malformed img tags
            content = re.sub(r'<img\s+alt=""?\s*src=', '<img alt="" src=', content)
            content = re.sub(r'<img([^>]*?)(?<!/)>', r'<img\1/>', content)
            
            # Fix any remaining quote issues in meta tags
            content = re.sub(r'<meta([^>]*?)content="([^"]*?)""([^>]*?)>', r'<meta\1content="\2"\3>', content)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_files.append(file_path.name)
                print(f"Fixed: {file_path.name}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Also check titlepage.xhtml in root
    titlepage_path = Path('comp_temp/titlepage.xhtml')
    if titlepage_path.exists():
        try:
            with open(titlepage_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Apply same fixes
            content = re.sub(r'charset="([^"]+)""', r'charset="\1"', content)
            content = re.sub(r'charset="([^"]+)"([^>]*?)"', r'charset="\1"\2', content)
            content = re.sub(r'\s+/\s*>', '/>', content)
            content = re.sub(r'<img\s+alt=""?\s*src=', '<img alt="" src=', content)
            content = re.sub(r'<img([^>]*?)(?<!/)>', r'<img\1/>', content)
            content = re.sub(r'<meta([^>]*?)content="([^"]*?)""([^>]*?)>', r'<meta\1content="\2"\3>', content)
            
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
        mimetype_path = Path('comp_temp/mimetype')
        if mimetype_path.exists():
            zip_ref.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk('comp_temp'):
            for file in files:
                if file == 'mimetype':
                    continue
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, 'comp_temp')
                zip_ref.write(file_path, arc_name)
    
    # Clean up
    import shutil
    shutil.rmtree('comp_temp')
    
    print(f"\nFixed {len(fixed_files)} files: {', '.join(fixed_files)}")
    print("EPUB repacked successfully.")

if __name__ == "__main__":
    fix_all_meta_issues()