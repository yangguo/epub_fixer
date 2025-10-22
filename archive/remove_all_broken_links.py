#!/usr/bin/env python3
import zipfile
import os
import re
import shutil
from collections import defaultdict

def remove_all_broken_links():
    # Create backup
    shutil.copy2('doing1.epub', 'doing1_backup_remove_links.epub')
    print("Created backup: doing1_backup_remove_links.epub")
    
    # Extract EPUB
    with zipfile.ZipFile('doing1.epub', 'r') as epub:
        epub.extractall('remove_links_epub')
    
    oebps_dir = 'remove_links_epub/OEBPS'
    
    # First, collect all existing anchors in all files
    existing_anchors = defaultdict(set)
    
    print("Scanning for existing anchors...")
    for filename in os.listdir(oebps_dir):
        if filename.endswith('.xhtml'):
            file_path = os.path.join(oebps_dir, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find all id attributes
            anchors = re.findall(r'id="([^"]+)"', content)
            existing_anchors[filename].update(anchors)
    
    print(f"Found anchors in {len(existing_anchors)} files")
    
    # Now fix index.xhtml by removing ALL broken links
    index_path = os.path.join(oebps_dir, 'index.xhtml')
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        links_removed = 0
        
        # Find all href links with fragments
        def check_and_replace_link(match):
            nonlocal links_removed
            full_link = match.group(1)
            link_text = match.group(2)
            
            if '#' in full_link:
                target_file, fragment = full_link.split('#', 1)
                if target_file and not target_file.startswith('http'):
                    # Check if target file exists and has the anchor
                    if target_file in existing_anchors:
                        if fragment not in existing_anchors[target_file]:
                            # Broken link - replace with just the text
                            links_removed += 1
                            return link_text
                    else:
                        # Target file doesn't exist - replace with just the text
                        links_removed += 1
                        return link_text
            
            # Keep the original link if it's valid
            return match.group(0)
        
        # Replace broken links with just their text content
        content = re.sub(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', check_and_replace_link, content)
        
        print(f"Removed {links_removed} broken links from index.xhtml")
        
        if content != original_content:
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("Fixed index.xhtml")
    
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
    
    create_epub('remove_links_epub', 'doing1.epub')
    print("EPUB repacked successfully!")
    
    # Clean up
    shutil.rmtree('remove_links_epub')

if __name__ == '__main__':
    remove_all_broken_links()