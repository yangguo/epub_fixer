#!/usr/bin/env python3
"""
Direct Meta Tag Fix Script
Targets the specific malformed meta tag pattern found in the EPUB files.
"""

import os
import zipfile
import re
from pathlib import Path

def fix_meta_tag_in_file(file_path):
    """Fix the specific malformed meta tag pattern in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Direct string replacement for the exact malformed pattern
        content = content.replace(
            'charset="utf-8" / />',
            'charset="utf-8"/>'
        )
        
        # Also handle variations with different spacing
        content = content.replace(
            'charset="utf-8"/ />',
            'charset="utf-8"/>'
        )
        
        content = content.replace(
            'charset="utf-8" //>',
            'charset="utf-8"/>'
        )
        
        # Handle the pattern with extra quote
        content = re.sub(
            r'charset=""utf-8"\s*/\s*/>',
            'charset="utf-8"/>',
            content
        )
        
        # General pattern for malformed meta tags with space before />
        content = re.sub(
            r'(<meta[^>]+)\s+/\s*/>',
            r'\1/>',
            content
        )
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def fix_epub_meta_tags(epub_path):
    """Extract EPUB, fix meta tags, and repack."""
    print(f"Processing {epub_path}...")
    
    # Create backup
    backup_path = f"{epub_path}.backup.meta"
    if os.path.exists(backup_path):
        os.remove(backup_path)
    os.rename(epub_path, backup_path)
    
    # Extract EPUB
    extract_dir = "temp_meta_fix"
    if os.path.exists(extract_dir):
        import shutil
        shutil.rmtree(extract_dir)
    
    with zipfile.ZipFile(backup_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # Fix all HTML files
    fixed_count = 0
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith(('.html', '.xhtml')):
                file_path = os.path.join(root, file)
                if fix_meta_tag_in_file(file_path):
                    fixed_count += 1
                    print(f"Fixed meta tag in: {file}")
    
    print(f"Fixed meta tags in {fixed_count} files")
    
    # Repack EPUB
    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, extract_dir)
                zip_ref.write(file_path, arc_path)
    
    # Clean up
    import shutil
    shutil.rmtree(extract_dir)
    
    print(f"EPUB repacked successfully. Backup saved as {backup_path}")

if __name__ == "__main__":
    epub_file = "future1.epub"
    if os.path.exists(epub_file):
        fix_epub_meta_tags(epub_file)
        print("\nRunning epubcheck to verify fixes...")
        os.system(f'java -jar epubcheck.jar "{epub_file}" > output.txt 2>&1')
        print("Check output.txt for validation results.")
    else:
        print(f"EPUB file {epub_file} not found!")