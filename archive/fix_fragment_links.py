#!/usr/bin/env python3
import zipfile
import os
import re
import shutil
from collections import defaultdict

def fix_fragment_links():
    """Fix fragment identifier errors in EPUB"""
    epub_path = "future1.epub"
    backup_path = f"{epub_path}.backup.fragments"
    
    # Create backup
    shutil.copy2(epub_path, backup_path)
    print(f"Created backup: {backup_path}")
    
    # Extract EPUB
    extract_dir = "temp_fix_fragments"
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    
    with zipfile.ZipFile(epub_path, 'r') as z:
        z.extractall(extract_dir)
    
    # Collect all fragment IDs from all HTML files
    fragment_ids = defaultdict(set)
    text_dir = os.path.join(extract_dir, "text")
    
    print("Collecting fragment IDs...")
    for filename in os.listdir(text_dir):
        if filename.endswith('.html'):
            filepath = os.path.join(text_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find all id attributes
            id_matches = re.findall(r'\bid=["\']([^"\'\']+)["\']', content)
            for id_val in id_matches:
                fragment_ids[filename].add(id_val)
    
    print(f"Found fragment IDs in {len(fragment_ids)} files")
    
    # Fix fragment links
    files_fixed = 0
    total_fixes = 0
    
    for filename in os.listdir(text_dir):
        if filename.endswith('.html'):
            filepath = os.path.join(text_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Find all href links with fragments
            href_pattern = r'href=["\']([^"\'\']+\.html)#([^"\'\']+)["\']'
            matches = re.findall(href_pattern, content)
            
            for target_file, fragment in matches:
                # Check if the fragment exists in the target file
                if target_file in fragment_ids and fragment not in fragment_ids[target_file]:
                    # Try to find a similar fragment ID
                    similar_fragment = find_similar_fragment(fragment, fragment_ids[target_file])
                    
                    if similar_fragment:
                        # Replace with similar fragment
                        old_href = f'{target_file}#{fragment}'
                        new_href = f'{target_file}#{similar_fragment}'
                        content = content.replace(f'href="{old_href}"', f'href="{new_href}"')
                        content = content.replace(f"href='{old_href}'", f"href='{new_href}'")
                        print(f"  Fixed: {old_href} -> {new_href}")
                        total_fixes += 1
                    else:
                        # Remove the fragment part, just link to the file
                        old_href = f'{target_file}#{fragment}'
                        new_href = target_file
                        content = content.replace(f'href="{old_href}"', f'href="{new_href}"')
                        content = content.replace(f"href='{old_href}'", f"href='{new_href}'")
                        print(f"  Removed fragment: {old_href} -> {new_href}")
                        total_fixes += 1
            
            # Also fix internal fragment links (same file)
            internal_pattern = r'href=["\']#([^"\'\']+)["\']'
            internal_matches = re.findall(internal_pattern, content)
            
            for fragment in internal_matches:
                if fragment not in fragment_ids[filename]:
                    # Try to find similar fragment
                    similar_fragment = find_similar_fragment(fragment, fragment_ids[filename])
                    
                    if similar_fragment:
                        content = content.replace(f'href="#{fragment}"', f'href="#{similar_fragment}"')
                        content = content.replace(f"href='#{fragment}'", f"href='#{similar_fragment}'")
                        print(f"  Fixed internal: #{fragment} -> #{similar_fragment}")
                        total_fixes += 1
                    else:
                        # Remove the href entirely or replace with #
                        content = content.replace(f'href="#{fragment}"', 'href="#"')
                        content = content.replace(f"href='#{fragment}'", "href='#'")
                        print(f"  Removed internal fragment: #{fragment}")
                        total_fixes += 1
            
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                files_fixed += 1
    
    print(f"\nFixed {total_fixes} fragment links in {files_fixed} files")
    
    # Repack EPUB
    print("Repacking EPUB...")
    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as z:
        # Add mimetype first (uncompressed)
        mimetype_path = os.path.join(extract_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            z.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == 'mimetype':
                    continue
                    
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, extract_dir)
                
                # Use appropriate compression
                if file.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    z.write(file_path, arc_path, compress_type=zipfile.ZIP_STORED)
                else:
                    z.write(file_path, arc_path, compress_type=zipfile.ZIP_DEFLATED)
    
    # Clean up
    shutil.rmtree(extract_dir)
    
    # Run epubcheck
    print("Running epubcheck...")
    os.system(f'java -jar epubcheck.jar "{epub_path}" > output.txt 2>&1')
    print("Validation complete. Check output.txt for results.")

def find_similar_fragment(target, available_fragments):
    """Find a similar fragment ID from available ones"""
    target_lower = target.lower()
    
    # Exact match (case insensitive)
    for frag in available_fragments:
        if frag.lower() == target_lower:
            return frag
    
    # Try removing common prefixes/suffixes
    target_clean = re.sub(r'^(fn|note|ref|link|anchor)[-_]?', '', target_lower)
    target_clean = re.sub(r'[-_]?(fn|note|ref|link|anchor)$', '', target_clean)
    
    for frag in available_fragments:
        frag_clean = re.sub(r'^(fn|note|ref|link|anchor)[-_]?', '', frag.lower())
        frag_clean = re.sub(r'[-_]?(fn|note|ref|link|anchor)$', '', frag_clean)
        
        if frag_clean == target_clean:
            return frag
    
    # Try numeric matching (e.g., fn-5 -> fn5)
    target_num = re.search(r'(\d+)', target)
    if target_num:
        target_number = target_num.group(1)
        for frag in available_fragments:
            if target_number in frag:
                return frag
    
    return None

if __name__ == "__main__":
    fix_fragment_links()