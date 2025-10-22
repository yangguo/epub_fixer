#!/usr/bin/env python3
import os
import re
import zipfile
import shutil
import subprocess
import sys
from pathlib import Path

def extract_epub(epub_path, extract_dir):
    """Extract EPUB file to directory"""
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir)
    
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print(f"Extracted EPUB to {extract_dir}")

def repack_epub_proper(extract_dir, epub_path):
    """Repack directory to EPUB file with proper structure"""
    if os.path.exists(epub_path):
        os.remove(epub_path)
    
    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=0) as zip_ref:
        # First, add mimetype file uncompressed and first
        mimetype_path = os.path.join(extract_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            zip_ref.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Then add all other files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == 'mimetype':  # Skip mimetype as we already added it
                    continue
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, extract_dir)
                zip_ref.write(file_path, arc_name)
    
    print(f"Repacked EPUB to {epub_path}")

def fix_malformed_tags(content):
    """Fix malformed meta and img tags"""
    # Fix meta tags with space before />
    content = re.sub(r'<meta([^>]*?)\s+/>', r'<meta\1 />', content)
    
    # Fix meta tags with / /> pattern
    content = re.sub(r'<meta([^>]*?)\s*/\s*/>', r'<meta\1 />', content)
    
    # Fix img tags with / /> pattern
    content = re.sub(r'<img([^>]*?)\s*/\s*/>', r'<img\1 />', content)
    
    # Fix malformed charset in meta tags
    content = re.sub(r'charset="utf-8"\s*/\s*/>', 'charset="utf-8" />', content)
    
    # Fix img tags with malformed alt attribute
    content = re.sub(r'<img\s+alt="\s*src="([^"]*?)"([^>]*?)>', r'<img alt="" src="\1"\2>', content)
    
    return content

def add_missing_fragment_ids(content, file_name, missing_fragments):
    """Add missing fragment IDs to XHTML content"""
    if not missing_fragments:
        return content
    
    # Get fragments that should be in this file
    file_fragments = [frag for frag in missing_fragments if frag['file'] == file_name]
    
    for fragment in file_fragments:
        frag_id = fragment['id']
        
        # Try to find a suitable place to add the ID
        # Look for headings first
        heading_patterns = [
            (r'(<h[1-6][^>]*>)', f'\\1<span id="{frag_id}"></span>'),
            (r'(<div[^>]*class="[^"]*chapter[^"]*"[^>]*>)', f'\\1<span id="{frag_id}"></span>'),
            (r'(<div[^>]*>)', f'\\1<span id="{frag_id}"></span>'),
            (r'(<body[^>]*>)', f'\\1<div id="{frag_id}"></div>')
        ]
        
        added = False
        for pattern, replacement in heading_patterns:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content, count=1)
                added = True
                break
        
        if not added:
            # Add to body as last resort
            content = re.sub(r'(<body[^>]*>)', f'\\1\n<div id="{frag_id}"></div>', content)
    
    return content

def extract_missing_fragments_from_ncx(ncx_path):
    """Extract missing fragment identifiers from NCX file"""
    fragments = []
    
    if not os.path.exists(ncx_path):
        return fragments
    
    try:
        with open(ncx_path, 'r', encoding='utf-8') as f:
            ncx_content = f.read()
        
        # Find all content src attributes with fragments
        pattern = r'<content\s+src="([^#]+)#([^"]+)"'
        matches = re.findall(pattern, ncx_content)
        
        for file_path, fragment_id in matches:
            fragments.append({
                'file': os.path.basename(file_path),
                'id': fragment_id
            })
    
    except Exception as e:
        print(f"Error reading NCX file: {e}")
    
    return fragments

def process_xhtml_file(file_path, missing_fragments=None):
    """Process a single XHTML file to fix issues"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        file_name = os.path.basename(file_path)
        
        # Apply fixes
        content = fix_malformed_tags(content)
        
        # Add missing fragment IDs if provided
        if missing_fragments:
            content = add_missing_fragment_ids(content, file_name, missing_fragments)
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def run_epubcheck(epub_path):
    """Run epubcheck on the EPUB file"""
    try:
        result = subprocess.run(
            ['java', '-jar', 'epubcheck.jar', epub_path],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        print("\n=== EPUBCHECK RESULTS ===")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("--- STDERR ---")
            print(result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error running epubcheck: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python fix_epub_proper.py <epub_file>")
        sys.exit(1)
    
    epub_file = sys.argv[1]
    if not os.path.exists(epub_file):
        print(f"EPUB file not found: {epub_file}")
        sys.exit(1)
    
    extract_dir = "temp_proper_extract"
    
    try:
        # Extract EPUB
        extract_epub(epub_file, extract_dir)
        
        # Find NCX file and extract missing fragments
        ncx_path = None
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith('.ncx'):
                    ncx_path = os.path.join(root, file)
                    break
        
        missing_fragments = []
        if ncx_path:
            missing_fragments = extract_missing_fragments_from_ncx(ncx_path)
            print(f"Found {len(missing_fragments)} missing fragment references")
        
        # Process all XHTML and HTML files
        files_fixed = 0
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith(('.xhtml', '.html')):
                    file_path = os.path.join(root, file)
                    if process_xhtml_file(file_path, missing_fragments):
                        files_fixed += 1
        
        print(f"\nFixed {files_fixed} files")
        
        # Repack EPUB properly
        repack_epub_proper(extract_dir, epub_file)
        
        # Run epubcheck
        print("\nRunning epubcheck...")
        success = run_epubcheck(epub_file)
        
        if success:
            print("\n✓ EPUB validation successful!")
        else:
            print("\n✗ EPUB validation failed. Check errors above.")
        
        # Cleanup
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()