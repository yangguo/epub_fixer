#!/usr/bin/env python3
"""
Emergency fix for FATAL(RSC-016) malformed meta tag errors
"""

import zipfile
import tempfile
import os
import re
import shutil

def fix_malformed_meta_tags(content):
    """Fix malformed meta tags with broken charset attributes"""
    
    # Fix charset with double quotes: charset=""UTF-8"" -> charset="UTF-8"
    content = re.sub(r'charset=""([^"]*)""', r'charset="\1"', content)
    content = re.sub(r'charset=""([^"]*)""', r'charset="\1"', content)
    
    # Fix malformed / /> endings
    content = re.sub(r'/ />', r' />', content)
    
    # Fix extra spaces before />
    content = re.sub(r'\s+/>', r' />', content)
    
    return content

def fix_ncx_text_issue(content):
    """Fix text not allowed in NCX file"""
    # Remove text content that's not inside proper XML elements
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        stripped = line.strip()
        # Skip standalone text lines
        if stripped and not stripped.startswith('<') and not stripped.startswith('<?'):
            continue
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def fix_ncx_fragment_identifiers(ncx_content, xhtml_files):
    """Fix fragment identifier issues in NCX by ensuring IDs exist"""
    
    # Extract all fragment identifiers from NCX
    fragment_pattern = r'href="[^"]*#([^"]+)"'
    ncx_fragments = set(re.findall(fragment_pattern, ncx_content))
    
    # Collect all existing IDs from XHTML files
    existing_ids = set()
    for file_path in xhtml_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ids = re.findall(r'id="([^"]+)"', content)
            existing_ids.update(ids)
        except:
            pass
    
    # Remove broken fragment references
    def fix_fragment_ref(match):
        href = match.group(0)
        if '#' in href:
            file_part, fragment = href.rsplit('#', 1)
            if fragment not in existing_ids:
                # Remove the fragment part
                return f'href="{file_part}"'
        return href
    
    ncx_content = re.sub(r'href="[^"]*#[^"]*"', fix_fragment_ref, ncx_content)
    return ncx_content

def emergency_fix_epub(epub_file):
    """Apply emergency fixes to EPUB"""
    print(f"Applying emergency fixes to {epub_file}")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract EPUB
        extract_dir = os.path.join(temp_dir, 'epub_extracted')
        with zipfile.ZipFile(epub_file, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Find all XHTML files
        xhtml_files = []
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith('.xhtml'):
                    file_path = os.path.join(root, file)
                    xhtml_files.append(file_path)
        
        # Fix malformed meta tags in XHTML files
        fixed_count = 0
        for file_path in xhtml_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                content = fix_malformed_meta_tags(content)
                
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    fixed_count += 1
                    print(f"Fixed meta tags: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"Error fixing {file_path}: {e}")
        
        # Fix NCX file
        ncx_files = []
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith('.ncx'):
                    ncx_files.append(os.path.join(root, file))
        
        for ncx_path in ncx_files:
            try:
                with open(ncx_path, 'r', encoding='utf-8') as f:
                    ncx_content = f.read()
                
                original_content = ncx_content
                ncx_content = fix_ncx_text_issue(ncx_content)
                ncx_content = fix_ncx_fragment_identifiers(ncx_content, xhtml_files)
                
                if ncx_content != original_content:
                    with open(ncx_path, 'w', encoding='utf-8') as f:
                        f.write(ncx_content)
                    print(f"Fixed NCX: {os.path.basename(ncx_path)}")
                    fixed_count += 1
            except Exception as e:
                print(f"Error fixing NCX {ncx_path}: {e}")
        
        if fixed_count > 0:
            # Create backup
            backup_file = f"{epub_file}.backup.emergency"
            shutil.copy2(epub_file, backup_file)
            print(f"Created backup: {backup_file}")
            
            # Repack EPUB
            # Remove existing EPUB
            if os.path.exists(epub_file):
                os.remove(epub_file)
            
            # Create new EPUB
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
                        arc_path = os.path.relpath(file_path, extract_dir)
                        zip_ref.write(file_path, arc_path)
            
            print(f"Emergency fixes applied. Fixed {fixed_count} files.")
            return True
        else:
            print("No fixes needed")
            return False

if __name__ == '__main__':
    import sys
    epub_file = sys.argv[1] if len(sys.argv) > 1 else 'doing1.epub'
    success = emergency_fix_epub(epub_file)
    if success:
        print("✅ Emergency fixes completed!")
    else:
        print("⚠️  No emergency fixes applied")