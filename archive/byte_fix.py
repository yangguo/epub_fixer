#!/usr/bin/env python3
import zipfile
import os
from pathlib import Path

def fix_byte_level_issues():
    """Fix meta tag issues at byte level"""
    
    # Extract EPUB
    with zipfile.ZipFile('doing1.epub', 'r') as zip_ref:
        zip_ref.extractall('byte_temp')
    
    fixed_files = []
    
    # Process all XHTML files in OEBPS
    oebps_dir = Path('byte_temp/OEBPS')
    for file_path in oebps_dir.glob('*.xhtml'):
        try:
            # Read as bytes first to see exact content
            with open(file_path, 'rb') as f:
                content_bytes = f.read()
            
            original_bytes = content_bytes
            
            # Fix the charset issue at byte level
            # Replace charset="utf-8" with charset="utf-8"
            content_bytes = content_bytes.replace(b'charset="utf-8"', b'charset="utf-8"')
            content_bytes = content_bytes.replace(b'charset="UTF-8"', b'charset="UTF-8"')
            
            if content_bytes != original_bytes:
                with open(file_path, 'wb') as f:
                    f.write(content_bytes)
                fixed_files.append(file_path.name)
                print(f"Fixed: {file_path.name}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Also check titlepage.xhtml in root
    titlepage_path = Path('byte_temp/titlepage.xhtml')
    if titlepage_path.exists():
        try:
            with open(titlepage_path, 'rb') as f:
                content_bytes = f.read()
            
            original_bytes = content_bytes
            content_bytes = content_bytes.replace(b'charset="utf-8"', b'charset="utf-8"')
            content_bytes = content_bytes.replace(b'charset="UTF-8"', b'charset="UTF-8"')
            
            if content_bytes != original_bytes:
                with open(titlepage_path, 'wb') as f:
                    f.write(content_bytes)
                fixed_files.append('titlepage.xhtml')
                print(f"Fixed: titlepage.xhtml")
                
        except Exception as e:
            print(f"Error processing titlepage.xhtml: {e}")
    
    # Repack EPUB with proper mimetype ordering
    with zipfile.ZipFile('doing1.epub', 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        # Add mimetype first (uncompressed)
        mimetype_path = Path('byte_temp/mimetype')
        if mimetype_path.exists():
            zip_ref.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk('byte_temp'):
            for file in files:
                if file == 'mimetype':
                    continue
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, 'byte_temp')
                zip_ref.write(file_path, arc_name)
    
    # Clean up
    import shutil
    shutil.rmtree('byte_temp')
    
    print(f"\nFixed {len(fixed_files)} files: {', '.join(fixed_files)}")
    print("EPUB repacked successfully.")

if __name__ == "__main__":
    fix_byte_level_issues()