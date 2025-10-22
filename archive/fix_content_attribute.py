#!/usr/bin/env python3
import zipfile
import os
import re
import shutil

def fix_content_attribute():
    # Create backup
    shutil.copy2('doing1.epub', 'doing1_backup_content.epub')
    print("Created backup: doing1_backup_content.epub")
    
    # Extract EPUB
    with zipfile.ZipFile('doing1.epub', 'r') as epub:
        epub.extractall('fix_content_epub')
    
    fixed_files = []
    
    # Process all XHTML files
    oebps_dir = 'fix_content_epub/OEBPS'
    if os.path.exists(oebps_dir):
        for filename in os.listdir(oebps_dir):
            if filename.endswith('.xhtml'):
                file_path = os.path.join(oebps_dir, filename)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Fix the malformed content attribute
                # Pattern: content="text/html; charset=utf-8/> -> content="text/html; charset=utf-8"/>
                # Pattern: content="text/html; charset=UTF-8/> -> content="text/html; charset=UTF-8"/>
                content = re.sub(r'content="([^"]*charset=[^"]*)/>', r'content="\1"/>', content)
                
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    fixed_files.append(filename)
                    print(f"Fixed content attribute in: {filename}")
    
    # Also check titlepage.xhtml in root
    titlepage_path = 'fix_content_epub/titlepage.xhtml'
    if os.path.exists(titlepage_path):
        with open(titlepage_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        content = re.sub(r'content="([^"]*charset=[^"]*)/>', r'content="\1"/>', content)
        
        if content != original_content:
            with open(titlepage_path, 'w', encoding='utf-8') as f:
                f.write(content)
            fixed_files.append('titlepage.xhtml')
            print(f"Fixed content attribute in: titlepage.xhtml")
    
    print(f"\nTotal files fixed: {len(fixed_files)}")
    
    # Repack EPUB
    def create_epub(source_dir, output_file):
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as epub:
            # Add mimetype first (uncompressed)
            mimetype_path = os.path.join(source_dir, 'mimetype')
            if os.path.exists(mimetype_path):
                epub.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
            
            # Add all other files
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    if file == 'mimetype':
                        continue
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, source_dir)
                    epub.write(file_path, arc_path)
    
    create_epub('fix_content_epub', 'doing1.epub')
    print("EPUB repacked successfully!")
    
    # Clean up
    shutil.rmtree('fix_content_epub')

if __name__ == '__main__':
    fix_content_attribute()