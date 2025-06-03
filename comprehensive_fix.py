#!/usr/bin/env python3
import os
import zipfile
import re
import shutil
from pathlib import Path
from fix_epub import (
    fix_charset_issues,
    fix_line_breaks_in_meta,
    fix_malformed_brackets,
    fix_meta_spacing_issues,
    fix_div_and_paragraph_elements,
    fix_css_references,
    fix_fragment_identifiers,
    clean_meta_encoding
)

def extract_epub(epub_path, extract_dir):
    """Extract EPUB file to directory"""
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print(f"Extracted {epub_path} to {extract_dir}")

def fix_malformed_meta_tags(file_path):
    """Fix malformed meta tags with multiple forward slashes"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Fix meta tags with multiple forward slashes before />
    content = re.sub(r'<meta([^>]*?)\s*/\s*/\s*/\s*/\s*/\s*/\s*/\s*/\s*/\s*/\s*/>', r'<meta\1 />', content)
    
    # Fix any remaining malformed meta tags
    content = re.sub(r'<meta([^>]*?)\s*/+\s*/>', r'<meta\1 />', content)
    
    # Fix charset attribute issues
    content = re.sub(r'charset="utf-8"/"', 'charset="utf-8"', content)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed malformed meta tags in {file_path}")
        return True
    return False

def create_missing_css_files(extract_dir):
    """Create missing CSS files"""
    styles_dir = os.path.join(extract_dir, 'e9781501154577', 'styles')
    os.makedirs(styles_dir, exist_ok=True)
    
    # Create 9781501154577.css
    css1_content = """/* Basic EPUB styles */
body {
    font-family: serif;
    margin: 1em;
    line-height: 1.4;
}

h1, h2, h3, h4, h5, h6 {
    font-weight: bold;
    margin: 1em 0 0.5em 0;
}

p {
    margin: 0 0 1em 0;
    text-indent: 1em;
}

.cover {
    text-align: center;
}
"""
    
    css1_path = os.path.join(styles_dir, '9781501154577.css')
    with open(css1_path, 'w', encoding='utf-8') as f:
        f.write(css1_content)
    print(f"Created {css1_path}")
    
    # Create SS_global.css
    css2_content = """/* Global styles */
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    padding: 0;
}

img {
    max-width: 100%;
    height: auto;
}

.center {
    text-align: center;
}
"""
    
    css2_path = os.path.join(styles_dir, 'SS_global.css')
    with open(css2_path, 'w', encoding='utf-8') as f:
        f.write(css2_content)
    print(f"Created {css2_path}")

def fix_content_opf(file_path):
    """Fix content.opf metadata issues"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Fix self-closing metadata tag
    content = re.sub(r'<metadata([^>]*?)\s*/>', r'<metadata\1>', content)
    
    # Ensure metadata has proper closing tag
    if '<metadata' in content and '</metadata>' not in content:
        # Find the end of metadata content and add closing tag
        metadata_start = content.find('<metadata')
        if metadata_start != -1:
            # Find the last dc: element
            last_dc_end = -1
            for match in re.finditer(r'</dc:[^>]+>', content):
                last_dc_end = match.end()
            
            if last_dc_end != -1:
                content = content[:last_dc_end] + '\n  </metadata>' + content[last_dc_end:]
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed content.opf metadata in {file_path}")
        return True
    return False

def apply_comprehensive_fixes(extract_dir):
    """Apply all comprehensive fixes to XHTML files in the extracted EPUB"""
    print("Applying comprehensive fixes to XHTML files...")
    
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith('.xhtml') or file.endswith('.html'):
                file_path = os.path.join(root, file)
                print(f"Fixing {file_path}...")
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Apply all fixes
                    content = fix_charset_issues(content)
                    content = fix_line_breaks_in_meta(content)
                    content = fix_malformed_brackets(content)
                    content = fix_meta_spacing_issues(content)
                    content = fix_div_and_paragraph_elements(content)
                    content = fix_css_references(content)
                    content = fix_fragment_identifiers(content)
                    content = clean_meta_encoding(content)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                        
                except Exception as e:
                    print(f"Error fixing {file_path}: {e}")

def repack_epub(extract_dir, output_path):
    """Repack directory into EPUB file"""
    if os.path.exists(output_path):
        os.remove(output_path)
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add mimetype first (uncompressed)
        mimetype_path = os.path.join(extract_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            zipf.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == 'mimetype':
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, extract_dir)
                zipf.write(file_path, arcname)
    
    print(f"Repacked EPUB to {output_path}")

def main():
    epub_file = 'cuba1_manually_fixed.epub'
    extract_dir = 'cuba1_comprehensive_fix'
    output_file = 'cuba1_final_complete.epub'
    
    print("Starting comprehensive EPUB fix...")
    
    # Extract EPUB
    extract_epub(epub_file, extract_dir)
    
    # Fix content.opf
    opf_path = os.path.join(extract_dir, 'content.opf')
    if os.path.exists(opf_path):
        fix_content_opf(opf_path)
    
    # Create missing CSS files
    create_missing_css_files(extract_dir)
    
    # Fix all XHTML files
    xhtml_dir = os.path.join(extract_dir, 'e9781501154577', 'xhtml')
    if os.path.exists(xhtml_dir):
        for file in os.listdir(xhtml_dir):
            if file.endswith('.xhtml'):
                file_path = os.path.join(xhtml_dir, file)
                fix_malformed_meta_tags(file_path)
    
    # Also fix root level XHTML files
    for file in os.listdir(extract_dir):
        if file.endswith('.xhtml'):
            file_path = os.path.join(extract_dir, file)
            fix_malformed_meta_tags(file_path)
    
    # Apply comprehensive fixes to XHTML files
    apply_comprehensive_fixes(extract_dir)
    
    # Repack EPUB
    repack_epub(extract_dir, output_file)
    
    print(f"Comprehensive fix complete! Output: {output_file}")

if __name__ == '__main__':
    main()