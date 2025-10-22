#!/usr/bin/env python3
import zipfile
import os
from pathlib import Path

def check_and_fix_charset():
    """Check and fix the charset issue"""
    
    # First, let's check what's actually in the current EPUB
    with zipfile.ZipFile('doing1.epub', 'r') as zip_ref:
        zip_ref.extractall('check_temp')
    
    print("Checking files for charset patterns...")
    
    for file_path in Path('check_temp').rglob('*.xhtml'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for various charset patterns
            if 'charset="utf-8""' in content:
                print(f"Found charset=\"utf-8\"\" in {file_path.relative_to('check_temp')}")
            elif 'charset="UTF-8""' in content:
                print(f"Found charset=\"UTF-8\"\" in {file_path.relative_to('check_temp')}")
            elif 'charset="utf-8"' in content:
                print(f"Found charset=\"utf-8\" (correct) in {file_path.relative_to('check_temp')}")
            elif 'charset="UTF-8"' in content:
                print(f"Found charset=\"UTF-8\" (correct) in {file_path.relative_to('check_temp')}")
            
            # Look for the specific line that's causing issues
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if 'meta' in line and 'charset' in line:
                    print(f"  Line {i}: {repr(line)}")
                    if len(line) > 65:
                        print(f"    Character at position 66: {repr(line[65])}")
                        print(f"    Around position 66: {repr(line[60:70])}")
                        
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    # Now let's try to fix the issue
    print("\nAttempting to fix...")
    fixed_files = []
    
    for file_path in Path('check_temp').rglob('*.xhtml'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Try multiple fix patterns
            # Fix charset="utf-8"" -> charset="utf-8"
            content = content.replace('charset="utf-8""', 'charset="utf-8"')
            content = content.replace('charset="UTF-8""', 'charset="UTF-8"')
            
            # Fix charset="utf-8" -> charset="utf-8" (remove extra quote)
            content = content.replace('charset="utf-8"', 'charset="utf-8"')
            content = content.replace('charset="UTF-8"', 'charset="UTF-8"')
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_files.append(file_path.relative_to('check_temp'))
                print(f"Fixed: {file_path.relative_to('check_temp')}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Repack EPUB
    with zipfile.ZipFile('doing1.epub', 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        # Add mimetype first (uncompressed)
        mimetype_path = Path('check_temp/mimetype')
        if mimetype_path.exists():
            zip_ref.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk('check_temp'):
            for file in files:
                if file == 'mimetype':
                    continue
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, 'check_temp')
                zip_ref.write(file_path, arc_name)
    
    # Clean up
    import shutil
    shutil.rmtree('check_temp')
    
    print(f"\nFixed {len(fixed_files)} files.")
    print("EPUB repacked successfully.")

if __name__ == "__main__":
    check_and_fix_charset()