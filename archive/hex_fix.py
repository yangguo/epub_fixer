#!/usr/bin/env python3
import zipfile
import os
from pathlib import Path

def fix_hex_charset_issue():
    """Fix the charset issue using exact hex patterns"""
    
    # Extract EPUB
    with zipfile.ZipFile('doing1.epub', 'r') as zip_ref:
        zip_ref.extractall('hex_temp')
    
    fixed_files = []
    
    # Process all XHTML files in OEBPS
    oebps_dir = Path('hex_temp/OEBPS')
    for file_path in oebps_dir.glob('*.xhtml'):
        try:
            # Read as bytes to handle exact sequence
            with open(file_path, 'rb') as f:
                content_bytes = f.read()
            
            original_bytes = content_bytes
            
            # From hex calculation:
            # Bad pattern: charset="utf-8""/> (with extra quote)
            # Bad hex: 636861727365743d227574662d3822222f3e
            # Good pattern: charset="utf-8"/> (correct)
            # Good hex: 636861727365743d227574662d38222f3e
            
            bad_pattern = bytes.fromhex('636861727365743d227574662d3822222f3e')
            good_pattern = bytes.fromhex('636861727365743d227574662d38222f3e')
            
            content_bytes = content_bytes.replace(bad_pattern, good_pattern)
            
            if content_bytes != original_bytes:
                with open(file_path, 'wb') as f:
                    f.write(content_bytes)
                fixed_files.append(file_path.name)
                print(f"Fixed: {file_path.name}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Also check titlepage.xhtml in root
    titlepage_path = Path('hex_temp/titlepage.xhtml')
    if titlepage_path.exists():
        try:
            with open(titlepage_path, 'rb') as f:
                content_bytes = f.read()
            
            original_bytes = content_bytes
            bad_pattern = bytes.fromhex('636861727365743d227574662d3822222f3e')
            good_pattern = bytes.fromhex('636861727365743d227574662d38222f3e')
            content_bytes = content_bytes.replace(bad_pattern, good_pattern)
            
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
        mimetype_path = Path('hex_temp/mimetype')
        if mimetype_path.exists():
            zip_ref.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk('hex_temp'):
            for file in files:
                if file == 'mimetype':
                    continue
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, 'hex_temp')
                zip_ref.write(file_path, arc_name)
    
    # Clean up
    import shutil
    shutil.rmtree('hex_temp')
    
    print(f"\nFixed {len(fixed_files)} files: {', '.join(fixed_files)}")
    print("EPUB repacked successfully.")

if __name__ == "__main__":
    fix_hex_charset_issue()