#!/usr/bin/env python3
import zipfile
import os
import re
import shutil

def fix_anchor_placement():
    # Create backup
    shutil.copy2('doing1.epub', 'doing1_backup_anchor_fix.epub')
    print("Created backup: doing1_backup_anchor_fix.epub")
    
    # Extract EPUB
    with zipfile.ZipFile('doing1.epub', 'r') as epub:
        epub.extractall('fix_anchor_epub')
    
    oebps_dir = 'fix_anchor_epub/OEBPS'
    fixed_files = []
    
    # Fix chapter03.xhtml and chapter07.xhtml
    for filename in ['chapter03.xhtml', 'chapter07.xhtml']:
        file_path = os.path.join(oebps_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Remove any standalone anchor tags that were added at the end
            # These are likely causing the validation errors
            content = re.sub(r'<a id="page\d+" title="\d+" class="calibre6"></a>\s*', '', content)
            
            # Instead, find existing page anchors and see what pattern they follow
            existing_page_pattern = re.search(r'<a id="page\d+"[^>]*class="calibre6"[^>]*>[^<]*</a>', content)
            
            if existing_page_pattern:
                print(f"Found existing page anchor pattern in {filename}: {existing_page_pattern.group()}")
                
                # Find the last existing page anchor to determine where to add new ones
                last_page_match = None
                for match in re.finditer(r'<a id="page(\d+)"[^>]*class="calibre6"[^>]*>', content):
                    last_page_match = match
                
                if last_page_match:
                    last_page_num = int(last_page_match.group(1))
                    insert_pos = last_page_match.end()
                    
                    # Find the end of the current paragraph or element
                    remaining_content = content[insert_pos:]
                    next_closing_tag = re.search(r'</[^>]+>', remaining_content)
                    if next_closing_tag:
                        insert_pos += next_closing_tag.end()
                    
                    # Add missing page anchors based on what's needed
                    missing_pages = []
                    if filename == 'chapter03.xhtml':
                        missing_pages = ['page61']
                    elif filename == 'chapter07.xhtml':
                        missing_pages = ['page173']
                    
                    # Create proper anchor elements within paragraph context
                    new_anchors = []
                    for page_id in missing_pages:
                        page_num = page_id.replace('page', '')
                        new_anchor = f'\n<p class="calibre3"><a id="{page_id}" title="{page_num}" class="calibre6"></a></p>'
                        new_anchors.append(new_anchor)
                    
                    if new_anchors:
                        content = content[:insert_pos] + ''.join(new_anchors) + content[insert_pos:]
                        print(f"Added {len(new_anchors)} properly formatted page anchors to {filename}")
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_files.append(filename)
    
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
    
    create_epub('fix_anchor_epub', 'doing1.epub')
    print("EPUB repacked successfully!")
    
    # Clean up
    shutil.rmtree('fix_anchor_epub')

if __name__ == '__main__':
    fix_anchor_placement()