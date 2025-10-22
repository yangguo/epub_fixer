#!/usr/bin/env python3
"""
Fix final UUID identifier and NCX consistency issues
"""

import uuid
import os
import re
import zipfile
import shutil

def fix_uuid_issues():
    """Fix UUID identifier and NCX consistency"""
    
    # Create a proper UUID
    proper_uuid = str(uuid.uuid4())
    
    # Extract EPUB
    if os.path.exists('doing2_uuid_fix'):
        shutil.rmtree('doing2_uuid_fix')
    
    with zipfile.ZipFile('doing2_validated.epub', 'r') as zip_ref:
        zip_ref.extractall('doing2_uuid_fix')
    
    # Fix OPF UUID
    opf_path = 'doing2_uuid_fix/OEBPS/content.opf'
    if os.path.exists(opf_path):
        with open(opf_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix the UUID to be properly formatted
        content = re.sub(r'urn:uuid:\d{14}', f'urn:uuid:{proper_uuid}', content)
        
        with open(opf_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    # Fix NCX identifier to match OPF
    ncx_path = 'doing2_uuid_fix/OEBPS/toc.ncx'
    if os.path.exists(ncx_path):
        with open(ncx_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix NCX identifier to match OPF
        content = re.sub(r'name="dtb:uid" content="bookid"', f'name="dtb:uid" content="urn:uuid:{proper_uuid}"', content)
        
        with open(ncx_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    # Repack
    with zipfile.ZipFile('doing2_perfect.epub', 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        # Mimetype first (uncompressed)
        zip_ref.write('doing2_uuid_fix/mimetype', 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # All other files
        for root, dirs, files in os.walk('doing2_uuid_fix'):
            for file in files:
                if file == 'mimetype':
                    continue
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, 'doing2_uuid_fix')
                zip_ref.write(file_path, arc_path)
    
    # Clean up
    shutil.rmtree('doing2_uuid_fix')
    
    print(f"Perfect EPUB created: doing2_perfect.epub")
    print(f"UUID used: {proper_uuid}")

if __name__ == '__main__':
    fix_uuid_issues()