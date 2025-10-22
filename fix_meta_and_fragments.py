#!/usr/bin/env python3
"""
Targeted EPUB fixer for meta tag and fragment identifier issues
"""

import os
import re
import zipfile
import tempfile
import shutil
import subprocess
import sys
from pathlib import Path

def extract_epub(epub_file, extract_dir):
    """Extract EPUB file to directory"""
    try:
        with zipfile.ZipFile(epub_file, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        return True
    except Exception as e:
        print(f"Error extracting EPUB: {e}")
        return False

def repack_epub(extract_dir, epub_file):
    """Repack directory into EPUB file"""
    try:
        with zipfile.ZipFile(epub_file, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            # Add mimetype first (uncompressed)
            mimetype_path = os.path.join(extract_dir, 'mimetype')
            if os.path.exists(mimetype_path):
                zip_ref.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
            
            # Add all other files
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file == 'mimetype':
                        continue
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, extract_dir)
                    zip_ref.write(file_path, arc_name)
        return True
    except Exception as e:
        print(f"Error repacking EPUB: {e}")
        return False

def fix_malformed_meta_tags(content):
    """Fix malformed meta tags with specific patterns found in the EPUB"""
    print("  Fixing malformed meta tags...")
    
    # Fix the specific patterns found in the EPUB:
    # 1. Fix meta tags with extra space before / />
    content = re.sub(r'<meta([^>]*?)\s+/\s+/>', r'<meta\1 />', content)
    
    # 2. Fix meta tags with malformed charset attribute
    content = re.sub(r'charset="utf-8"\s+/\s+/>', r'charset="utf-8" />', content)
    
    # 3. Fix img tags with malformed alt and src attributes
    content = re.sub(r'<img\s+alt="([^"]*?)\s+src="([^"]*?)"([^>]*?)\s+/\s+/>', r'<img alt="\1" src="\2"\3 />', content)
    
    # 4. More general fix for any tag with / /> pattern
    content = re.sub(r'\s+/\s+/>', r' />', content)
    
    # 5. Fix malformed quotes in attributes
    content = re.sub(r'charset="utf-8"\s+/\s+/>', r'charset="utf-8" />', content)
    
    return content

def fix_malformed_img_tags(content):
    """Fix malformed img tags"""
    print("  Fixing malformed img tags...")
    
    # Fix img tags with missing quotes or malformed attributes
    # Pattern: <img alt=" src="..." becomes <img alt="" src="..."
    content = re.sub(r'<img\s+alt="\s+src="([^"]*?)"([^>]*?)\s*/\s*/>', r'<img alt="" src="\1"\2 />', content)
    
    return content

def extract_fragment_ids_from_ncx(ncx_content):
    """Extract all fragment identifiers referenced in NCX file"""
    fragments = {}
    
    # Find all content src attributes with fragments
    pattern = r'<content\s+src\s*=\s*["\']([^"\'>]+?)#([^"\'>]+)["\']'
    matches = re.findall(pattern, ncx_content)
    
    for file_path, fragment_id in matches:
        if file_path not in fragments:
            fragments[file_path] = set()
        fragments[file_path].add(fragment_id)
    
    return fragments

def add_missing_fragment_ids(file_path, fragment_ids):
    """Add missing fragment IDs to an XHTML file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find existing IDs
        existing_ids = set(re.findall(r'id\s*=\s*["\']([^"\'>]+)["\']', content))
        
        # Find missing IDs
        missing_ids = fragment_ids - existing_ids
        
        if not missing_ids:
            return False
        
        print(f"    Adding {len(missing_ids)} missing fragment IDs to {os.path.basename(file_path)}")
        
        # Add missing IDs to appropriate elements
        for fragment_id in missing_ids:
            # Try to find a suitable place to add the ID
            # Look for headings, divs, or other block elements
            patterns_to_try = [
                # Add to headings that might match the fragment name
                (rf'(<h[1-6][^>]*>)([^<]*{re.escape(fragment_id.replace("_", " ").replace("-", " "))}[^<]*)', rf'\1<span id="{fragment_id}"></span>\2'),
                # Add to divs or sections
                (r'(<div[^>]*class="[^"]*"[^>]*>)', rf'\1<span id="{fragment_id}"></span>'),
                (r'(<section[^>]*>)', rf'\1<span id="{fragment_id}"></span>'),
                # Add to paragraphs as last resort
                (r'(<p[^>]*>)', rf'\1<span id="{fragment_id}"></span>'),
            ]
            
            added = False
            for pattern, replacement in patterns_to_try:
                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content, count=1)
                    added = True
                    break
            
            # If no suitable place found, add to body
            if not added:
                body_pattern = r'(<body[^>]*>)'
                if re.search(body_pattern, content):
                    content = re.sub(body_pattern, rf'\1\n<div id="{fragment_id}"></div>', content, count=1)
                    added = True
            
            # Last resort: add at the end of body
            if not added:
                content = re.sub(r'(</body>)', rf'<div id="{fragment_id}"></div>\n\1', content)
        
        # Write back the modified content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
        
    except Exception as e:
        print(f"Error adding fragment IDs to {file_path}: {e}")
        return False

def run_epubcheck(epub_file, output_file):
    """Run epubcheck on the EPUB file"""
    try:
        cmd = ['java', '-jar', 'epubcheck.jar', epub_file]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        # Write output to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n--- STDERR ---\n")
                f.write(result.stderr)
        
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        print(f"Error running epubcheck: {e}")
        return False, str(e)

def main():
    epub_file = 'doing2.epub'
    output_file = 'fixed_output.txt'
    
    if not os.path.exists(epub_file):
        print(f"Error: {epub_file} not found")
        return False
    
    print(f"Fixing meta tags and fragment identifiers in: {epub_file}")
    
    # Create temporary directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        extract_dir = os.path.join(temp_dir, 'epub_extracted')
        
        # Extract EPUB
        if not extract_epub(epub_file, extract_dir):
            print("Failed to extract EPUB")
            return False
        
        print("Extracted EPUB successfully")
        
        # Fix meta tags and img tags in all XHTML files
        fixed_files = []
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith(('.xhtml', '.html')):
                    file_path = os.path.join(root, file)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        original_content = content
                        print(f"Processing: {os.path.basename(file_path)}")
                        
                        content = fix_malformed_meta_tags(content)
                        content = fix_malformed_img_tags(content)
                        
                        if content != original_content:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            fixed_files.append(file_path)
                            print(f"  ✓ Fixed: {os.path.basename(file_path)}")
                        else:
                            print(f"  - No changes needed: {os.path.basename(file_path)}")
                            
                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")
        
        # Fix fragment identifiers
        ncx_path = None
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith('.ncx'):
                    ncx_path = os.path.join(root, file)
                    break
        
        if ncx_path and os.path.exists(ncx_path):
            print("\nFixing fragment identifiers...")
            
            with open(ncx_path, 'r', encoding='utf-8') as f:
                ncx_content = f.read()
            
            # Extract fragment requirements from NCX
            fragments_needed = extract_fragment_ids_from_ncx(ncx_content)
            print(f"Found {sum(len(frags) for frags in fragments_needed.values())} fragment references in NCX")
            
            # Add missing fragments to XHTML files
            for file_path, fragment_ids in fragments_needed.items():
                # Find the actual file path
                target_file = None
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        if file == os.path.basename(file_path) or file_path.endswith(file):
                            target_file = os.path.join(root, file)
                            break
                    if target_file:
                        break
                
                if target_file and os.path.exists(target_file):
                    print(f"  Processing fragments for: {os.path.basename(file_path)}")
                    if add_missing_fragment_ids(target_file, fragment_ids):
                        if target_file not in fixed_files:
                            fixed_files.append(target_file)
                else:
                    print(f"  Warning: Could not find file {file_path}")
        
        if fixed_files:
            print(f"\nFixed {len(fixed_files)} files total")
            
            # Create backup
            backup_file = f"{epub_file}.backup.meta_fix"
            if not os.path.exists(backup_file):
                shutil.copy2(epub_file, backup_file)
                print(f"Created backup: {backup_file}")
            
            # Repack EPUB
            if not repack_epub(extract_dir, epub_file):
                print("Failed to repack EPUB")
                return False
            
            print("Repacked EPUB successfully")
        else:
            print("No files needed fixing")
        
        # Run epubcheck
        print("\nRunning epubcheck...")
        success, output = run_epubcheck(epub_file, output_file)
        
        # Count errors and warnings
        error_count = output.count('ERROR(')
        warning_count = output.count('WARNING(')
        fatal_count = output.count('FATAL(')
        
        print(f"\nValidation results:")
        print(f"Fatals: {fatal_count}, Errors: {error_count}, Warnings: {warning_count}")
        print(f"Results saved to: {output_file}")
        
        if success or (fatal_count == 0 and error_count == 0):
            print("\n✅ EPUB is now valid!")
            return True
        else:
            print("\n⚠️  Some issues remain")
            return False

if __name__ == '__main__':
    success = main()
    if not success:
        sys.exit(1)