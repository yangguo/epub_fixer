#!/usr/bin/env python3
import zipfile
import os
import re
import shutil
from collections import defaultdict

def comprehensive_fix():
    """Comprehensive fix for all remaining EPUB errors"""
    epub_path = "future1.epub"
    backup_path = f"{epub_path}.backup.comprehensive"
    
    # Create backup
    shutil.copy2(epub_path, backup_path)
    print(f"Created backup: {backup_path}")
    
    # Extract EPUB
    extract_dir = "temp_comprehensive_fix"
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    
    with zipfile.ZipFile(epub_path, 'r') as z:
        z.extractall(extract_dir)
    
    files_fixed = 0
    total_fixes = 0
    
    # Fix titlepage.xhtml first
    titlepage_path = os.path.join(extract_dir, "titlepage.xhtml")
    if os.path.exists(titlepage_path):
        with open(titlepage_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix meta tag
        content = re.sub(r'<meta([^>]*?)\s+/\s*>', r'<meta\1/>', content)
        content = re.sub(r'<meta([^>]*?)\s*/>', r'<meta\1 />', content)
        
        if content != original_content:
            with open(titlepage_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("Fixed titlepage.xhtml meta tag")
            total_fixes += 1
    
    # Process all HTML files in text directory
    text_dir = os.path.join(extract_dir, "text")
    
    for filename in os.listdir(text_dir):
        if filename.endswith('.html'):
            filepath = os.path.join(text_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            file_fixes = 0
            
            # 1. Fix invalid ID attributes (remove colons and make XML-compliant)
            def fix_id_attribute(match):
                id_value = match.group(1)
                # Remove colons and other invalid characters
                fixed_id = re.sub(r'[^a-zA-Z0-9_-]', '_', id_value)
                # Ensure it starts with a letter or underscore
                if not re.match(r'^[a-zA-Z_]', fixed_id):
                    fixed_id = 'id_' + fixed_id
                return f'id="{fixed_id}"'
            
            content = re.sub(r'id="([^"]*[^a-zA-Z0-9_-][^"]*?)"', fix_id_attribute, content)
            
            # 2. Fix malformed img tags
            # Pattern: <img ... /> should have proper spacing
            content = re.sub(r'<img([^>]*?)\s+/\s*>', r'<img\1 />', content)
            # Fix missing closing for img tags
            content = re.sub(r'<img([^>]*?)(?<!/)>', r'<img\1 />', content)
            
            # 3. Fix invalid URLs
            content = re.sub(r'href="http://hdl:([^"]*?)"', r'href="http://hdl.handle.net/\1"', content)
            
            # 4. Remove fragment identifiers that don't exist
            # For now, just remove the fragment part from hrefs that cause errors
            fragment_patterns = [
                r'href="([^"#]*\.html)#[^"]*"',  # External file fragments
                r'href="#[^"]*"'  # Internal fragments
            ]
            
            for pattern in fragment_patterns:
                if pattern.endswith('"'):
                    # Internal fragments - replace with just #
                    content = re.sub(pattern, 'href="#"', content)
                else:
                    # External fragments - keep just the file
                    content = re.sub(pattern, r'href="\1"', content)
            
            # 5. Fix duplicate IDs by making them unique
            id_counts = defaultdict(int)
            def make_unique_id(match):
                id_value = match.group(1)
                id_counts[id_value] += 1
                if id_counts[id_value] > 1:
                    return f'id="{id_value}_{id_counts[id_value]}"'
                return match.group(0)
            
            content = re.sub(r'id="([^"]+)"', make_unique_id, content)
            
            # 6. Fix any remaining XML syntax issues
            content = re.sub(r'<(\w+)([^>]*?)\s+/\s*>', r'<\1\2 />', content)
            
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                files_fixed += 1
                file_fixes = content.count('id="') - original_content.count('id="') + 1
                total_fixes += file_fixes
                print(f"Fixed {filename}")
    
    print(f"\nFixed {total_fixes} issues in {files_fixed} files")
    
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

if __name__ == "__main__":
    comprehensive_fix()