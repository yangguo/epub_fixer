#!/usr/bin/env python3
import zipfile
import os
from pathlib import Path

def fix_exact_charset_issue():
    """Fix the exact charset quote issue"""
    
    # Extract EPUB
    with zipfile.ZipFile('doing1.epub', 'r') as zip_ref:
        zip_ref.extractall('exact_temp')
    
    fixed_files = []
    
    # Process all XHTML files in OEBPS
    oebps_dir = Path('exact_temp/OEBPS')
    for file_path in oebps_dir.glob('*.xhtml'):
        try:
            # Read as bytes to handle exact sequence
            with open(file_path, 'rb') as f:
                content_bytes = f.read()
            
            original_bytes = content_bytes
            
            # Fix the exact issue: charset="utf-8" -> charset="utf-8"
            # The problematic sequence is: charset="utf-8"
            content_bytes = content_bytes.replace(b'charset="utf-8"', b'charset="utf-8"')
            
            if content_bytes != original_bytes:
                with open(file_path, 'wb') as f:
                    f.write(content_bytes)
                fixed_files.append(file_path.name)
                print(f"Fixed: {file_path.name}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Also check titlepage.xhtml in root
    titlepage_path = Path('exact_temp/titlepage.xhtml')
    if titlepage_path.exists():
        try:
            with open(titlepage_path, 'rb') as f:
                content_bytes = f.read()
            
            original_bytes = content_bytes
            content_bytes = content_bytes.replace(b'charset="utf-8"', b'charset="utf-8"')
            
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
        mimetype_path = Path('exact_temp/mimetype')
        if mimetype_path.exists():
            zip_ref.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk('exact_temp'):
            for file in files:
                if file == 'mimetype':
                    continue
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, 'exact_temp')
                zip_ref.write(file_path, arc_name)
    
    # Clean up
    import shutil
    shutil.rmtree('exact_temp')
    
    print(f"\nFixed {len(fixed_files)} files: {', '.join(fixed_files)}")
    print("EPUB repacked successfully.")

if __name__ == "__main__":
    fix_exact_charset_issue()