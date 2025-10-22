#!/usr/bin/env python3
import os
import zipfile
import shutil
from pathlib import Path
import re

def fix_xhtml_indentation(content):
    """
    Fix indentation issues in XHTML files that might cause XML parsing errors.
    """
    lines = content.split('\n')
    fixed_lines = []
    indent_level = 0
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            fixed_lines.append('')
            continue
            
        # Handle closing tags
        if stripped.startswith('</') and not stripped.startswith('</meta') and not stripped.startswith('</link'):
            indent_level = max(0, indent_level - 1)
        
        # Apply proper indentation
        if stripped.startswith('<?xml') or stripped.startswith('<!DOCTYPE'):
            # XML declaration and DOCTYPE should not be indented
            fixed_lines.append(stripped)
        else:
            # Apply consistent 2-space indentation
            fixed_lines.append('  ' * indent_level + stripped)
        
        # Handle opening tags (but not self-closing tags)
        if (stripped.startswith('<') and not stripped.startswith('</') and 
            not stripped.endswith('/>') and not stripped.startswith('<?') and 
            not stripped.startswith('<!')):
            # Check if it's a self-closing tag written without />
            if not any(tag in stripped for tag in ['<meta', '<link', '<img', '<br', '<hr']):
                indent_level += 1
    
    return '\n'.join(fixed_lines)

def fix_epub_indentation():
    epub_file = 'doing1.epub'
    
    # Create backup
    backup_num = 1
    while os.path.exists(f'{epub_file}.backup.{backup_num}'):
        backup_num += 1
    shutil.copy2(epub_file, f'{epub_file}.backup.{backup_num}')
    print(f"Created backup: {epub_file}.backup.{backup_num}")
    
    # Extract EPUB
    extract_dir = 'debug4_epub'
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    
    with zipfile.ZipFile(epub_file, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    print(f"Extracted EPUB to {extract_dir}")
    
    # Fix all XHTML files
    xhtml_dir = Path(extract_dir) / 'OEBPS'
    files_fixed = 0
    
    for xhtml_file in xhtml_dir.glob('*.xhtml'):
        print(f"Processing {xhtml_file.name}...")
        
        with open(xhtml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix indentation
        fixed_content = fix_xhtml_indentation(content)
        
        # Only write if content changed
        if fixed_content != content:
            print(f"  Fixed indentation in {xhtml_file.name}")
            with open(xhtml_file, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            files_fixed += 1
    
    # Also check titlepage.xhtml in root
    titlepage_file = Path(extract_dir) / 'titlepage.xhtml'
    if titlepage_file.exists():
        print(f"Processing titlepage.xhtml...")
        with open(titlepage_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        fixed_content = fix_xhtml_indentation(content)
        
        if fixed_content != content:
            print(f"  Fixed indentation in titlepage.xhtml")
            with open(titlepage_file, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            files_fixed += 1
    
    print(f"Fixed {files_fixed} files")
    
    # Repack EPUB
    print("Repacking EPUB...")
    
    # Remove old EPUB
    os.remove(epub_file)
    
    # Create new EPUB
    with zipfile.ZipFile(epub_file, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        # Add mimetype first (uncompressed)
        mimetype_path = Path(extract_dir) / 'mimetype'
        if mimetype_path.exists():
            zip_ref.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == 'mimetype':
                    continue  # Already added
                file_path = Path(root) / file
                arcname = file_path.relative_to(extract_dir)
                zip_ref.write(file_path, arcname)
    
    print(f"EPUB repacked successfully")
    
    # Clean up
    shutil.rmtree(extract_dir)
    print(f"Cleaned up temporary directory")

if __name__ == '__main__':
    fix_epub_indentation()