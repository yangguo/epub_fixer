#!/usr/bin/env python3
import os
import zipfile
import shutil
from pathlib import Path

def fix_xhtml_head_structure(content):
    """
    Fix the head section structure in XHTML files.
    The issue is that the head section is not properly closed.
    """
    lines = content.split('\n')
    fixed_lines = []
    in_head = False
    head_closed = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Track if we're in the head section
        if '<head>' in stripped:
            in_head = True
            head_closed = False
        elif '</head>' in stripped:
            in_head = False
            head_closed = True
        
        # If we encounter a body tag and head hasn't been closed, close it
        if '<body' in stripped and in_head and not head_closed:
            # Insert </head> before the body tag
            fixed_lines.append('</head>')
            in_head = False
            head_closed = True
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def fix_epub_structure():
    epub_file = 'doing1.epub'
    
    # Create backup
    backup_num = 1
    while os.path.exists(f'{epub_file}.backup.{backup_num}'):
        backup_num += 1
    shutil.copy2(epub_file, f'{epub_file}.backup.{backup_num}')
    print(f"Created backup: {epub_file}.backup.{backup_num}")
    
    # Extract EPUB
    extract_dir = 'debug3_epub'
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
        
        # Check if head section needs fixing
        if '<head>' in content and '</head>' not in content:
            print(f"  Fixing head structure in {xhtml_file.name}")
            fixed_content = fix_xhtml_head_structure(content)
            
            with open(xhtml_file, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            files_fixed += 1
        elif '<head>' in content and content.count('<head>') != content.count('</head>'):
            print(f"  Head tag mismatch in {xhtml_file.name}, fixing...")
            fixed_content = fix_xhtml_head_structure(content)
            
            with open(xhtml_file, 'w', encoding='utf-8') as f:
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
    fix_epub_structure()