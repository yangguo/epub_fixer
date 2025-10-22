#!/usr/bin/env python3
"""
Fix EPUB structure issues - reorganize files properly
"""

import os
import re
import zipfile
import shutil

def fix_epub_structure():
    """Completely restructure the EPUB"""
    
    # Create new structure
    if os.path.exists('doing2_fixed'):
        shutil.rmtree('doing2_fixed')
    
    os.makedirs('doing2_fixed/META-INF', exist_ok=True)
    os.makedirs('doing2_fixed/OEBPS', exist_ok=True)
    
    # Extract current EPUB
    with zipfile.ZipFile('doing2.epub', 'r') as zip_ref:
        zip_ref.extractall('doing2_temp')
    
    # Move files to proper structure
    temp_dir = 'doing2_temp'
    
    # Move mimetype
    if os.path.exists(os.path.join(temp_dir, 'mimetype')):
        shutil.move(os.path.join(temp_dir, 'mimetype'), 'doing2_fixed/mimetype')
    
    # Move META-INF files
    if os.path.exists(os.path.join(temp_dir, 'META-INF')):
        for file in os.listdir(os.path.join(temp_dir, 'META-INF')):
            shutil.move(os.path.join(temp_dir, 'META-INF', file), 'doing2_fixed/META-INF')
    
    # Move OEBPS files
    if os.path.exists(os.path.join(temp_dir, 'OEBPS')):
        for file in os.listdir(os.path.join(temp_dir, 'OEBPS')):
            shutil.move(os.path.join(temp_dir, 'OEBPS', file), 'doing2_fixed/OEBPS')
    
    # Move root level files to OEBPS
    for file in os.listdir(temp_dir):
        if file not in ['META-INF', 'mimetype', 'OEBPS']:
            if os.path.isfile(os.path.join(temp_dir, file)):
                shutil.move(os.path.join(temp_dir, file), 'doing2_fixed/OEBPS')
    
    # Clean up temp
    shutil.rmtree(temp_dir)
    
    # Fix file paths in content.opf
    fix_opf_paths('doing2_fixed/OEBPS/content.opf')
    
    # Repack
    with zipfile.ZipFile('doing2_structured.epub', 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        # Add mimetype first
        zip_ref.write('doing2_fixed/mimetype', 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all files
        for root, dirs, files in os.walk('doing2_fixed'):
            for file in files:
                if file == 'mimetype':
                    continue
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, 'doing2_fixed')
                zip_ref.write(file_path, arc_path)
    
    print("EPUB restructured successfully")

def fix_opf_paths(opf_path):
    """Fix file paths in OPF"""
    with open(opf_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix href attributes to use proper paths
    content = re.sub(r'href="([^/"]+)"', r'href="\1"', content)
    content = re.sub(r'href="OEBPS/([^"]+)"', r'href="\1"', content)
    
    # Ensure proper package structure
    content = re.sub(r'<package[^>]*>', '<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="uuid_id">', content)
    
    # Fix metadata
    content = re.sub(r'<metadata[^>]*>', '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">', content)
    
    with open(opf_path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    fix_epub_structure()