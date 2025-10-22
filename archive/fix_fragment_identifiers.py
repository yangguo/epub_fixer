#!/usr/bin/env python3
import zipfile
import os
import re
import shutil
from collections import defaultdict

def fix_fragment_identifiers():
    # Create backup
    shutil.copy2('doing1.epub', 'doing1_backup_fragments.epub')
    print("Created backup: doing1_backup_fragments.epub")
    
    # Extract EPUB
    with zipfile.ZipFile('doing1.epub', 'r') as epub:
        epub.extractall('fix_fragments_epub')
    
    # First, collect all existing anchors in all files
    existing_anchors = defaultdict(set)
    oebps_dir = 'fix_fragments_epub/OEBPS'
    
    print("Scanning for existing anchors...")
    for filename in os.listdir(oebps_dir):
        if filename.endswith('.xhtml'):
            file_path = os.path.join(oebps_dir, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find all id attributes
            anchors = re.findall(r'id="([^"]+)"', content)
            existing_anchors[filename].update(anchors)
            print(f"  {filename}: {len(anchors)} anchors")
    
    # Now scan for all links and check if targets exist
    broken_links = []
    all_links = []
    
    print("\nScanning for links...")
    for filename in os.listdir(oebps_dir):
        if filename.endswith('.xhtml'):
            file_path = os.path.join(oebps_dir, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find all href links with fragments
            links = re.findall(r'href="([^"]+#[^"]+)"', content)
            for link in links:
                all_links.append((filename, link))
                
                # Parse the link
                if '#' in link:
                    target_file, fragment = link.split('#', 1)
                    if target_file and not target_file.startswith('http'):
                        # Check if target file exists and has the anchor
                        if target_file in existing_anchors:
                            if fragment not in existing_anchors[target_file]:
                                broken_links.append((filename, link, target_file, fragment))
                        else:
                            broken_links.append((filename, link, target_file, fragment))
    
    print(f"\nFound {len(all_links)} total links")
    print(f"Found {len(broken_links)} broken fragment links")
    
    if broken_links:
        print("\nBroken links:")
        for source, link, target, fragment in broken_links[:10]:  # Show first 10
            print(f"  {source} -> {link} (missing {fragment} in {target})")
    
    # Strategy: Remove broken links from index.xhtml only (since that's where most errors are)
    # and create missing page anchors in chapter files
    
    fixed_files = []
    
    # Fix index.xhtml by removing broken links
    index_path = os.path.join(oebps_dir, 'index.xhtml')
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Remove links that point to non-existent fragments
        for source, link, target, fragment in broken_links:
            if source == 'index.xhtml':
                # Replace the broken link with just the text
                pattern = rf'<a href="{re.escape(link)}"[^>]*>([^<]+)</a>'
                content = re.sub(pattern, r'\1', content)
        
        if content != original_content:
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(content)
            fixed_files.append('index.xhtml')
            print(f"\nFixed broken links in: index.xhtml")
    
    # Also add missing page anchors to chapter files if they're commonly referenced
    missing_pages = defaultdict(list)
    for source, link, target, fragment in broken_links:
        if fragment.startswith('page') and target.startswith('chapter'):
            missing_pages[target].append(fragment)
    
    for target_file, missing_fragments in missing_pages.items():
        if len(missing_fragments) > 5:  # Only fix files with many missing pages
            file_path = os.path.join(oebps_dir, target_file)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Add missing page anchors at the end of the body
                missing_anchors_html = '\n'.join([
                    f'<a id="{fragment}" title="{fragment[4:]}" class="calibre6"></a>'
                    for fragment in set(missing_fragments)
                ])
                
                # Insert before closing body tag
                content = content.replace('</body>', f'{missing_anchors_html}\n</body>')
                
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    fixed_files.append(target_file)
                    print(f"Added {len(set(missing_fragments))} missing page anchors to: {target_file}")
    
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
    
    create_epub('fix_fragments_epub', 'doing1.epub')
    print("EPUB repacked successfully!")
    
    # Clean up
    shutil.rmtree('fix_fragments_epub')

if __name__ == '__main__':
    fix_fragment_identifiers()