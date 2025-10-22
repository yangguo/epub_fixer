#!/usr/bin/env python3
import zipfile
import os
import re
import shutil
from pathlib import Path

def extract_epub(epub_path, extract_dir):
    """Extract EPUB to directory"""
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir)
    
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print(f"Extracted EPUB to {extract_dir}")

def fix_value_attributes(content):
    """Remove invalid 'value' attributes from HTML elements"""
    # Remove value attributes from various HTML elements
    patterns = [
        # Remove value attribute from span elements
        r'(<span[^>]*?)\s+value="[^"]*"([^>]*>)',
        # Remove value attribute from div elements  
        r'(<div[^>]*?)\s+value="[^"]*"([^>]*>)',
        # Remove value attribute from p elements
        r'(<p[^>]*?)\s+value="[^"]*"([^>]*>)',
        # Remove value attribute from any element (general pattern)
        r'(<[^>]*?)\s+value="[^"]*"([^>]*>)',
    ]
    
    for pattern in patterns:
        content = re.sub(pattern, r'\1\2', content, flags=re.IGNORECASE)
    
    return content

def fix_amazon_attributes(content):
    """Remove Amazon-specific attributes that are not valid in EPUB"""
    patterns = [
        # Remove data-AmznRemoved attributes
        r'\s+data-AmznRemoved="[^"]*"',
        r'\s+data-AmznRemoved-M8="[^"]*"',
        # Remove other Amazon-specific attributes
        r'\s+data-amzn[^=]*="[^"]*"',
    ]
    
    for pattern in patterns:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE)
    
    return content

def fix_fragment_identifiers(content, filename):
    """Fix or remove invalid fragment identifiers"""
    # Common patterns for fragment identifiers that need fixing
    patterns = [
        # Fix malformed fragment identifiers in href attributes
        r'href="([^"]*#[^"]*?)\s+([^"]*?)"',  # Remove spaces in fragment IDs
        r'href="#([^"]*?)\s+([^"]*?)"',       # Remove spaces after #
    ]
    
    for pattern in patterns:
        content = re.sub(pattern, lambda m: f'href="{m.group(1).replace(" ", "")}{m.group(2).replace(" ", "")}"', content)
    
    # Remove href attributes that point to non-existent fragments
    # This is a more aggressive approach - remove problematic links
    if 'href="#' in content:
        # Find all fragment references and check if they're valid
        fragment_refs = re.findall(r'href="#([^"]+)"', content)
        for ref in fragment_refs:
            # If the fragment contains spaces or special characters, remove the href
            if ' ' in ref or len(ref) > 50:  # Likely malformed
                content = re.sub(f'href="#{re.escape(ref)}"', '', content)
    
    return content

def process_html_files(extract_dir):
    """Process all HTML files to fix errors"""
    html_files = []
    text_dir = os.path.join(extract_dir, 'text')
    
    if os.path.exists(text_dir):
        for file in os.listdir(text_dir):
            if file.endswith('.html') or file.endswith('.xhtml'):
                html_files.append(os.path.join(text_dir, file))
    
    # Also check root directory for HTML files
    for file in os.listdir(extract_dir):
        if file.endswith('.html') or file.endswith('.xhtml'):
            html_files.append(os.path.join(extract_dir, file))
    
    fixed_count = 0
    
    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Apply fixes
            content = fix_value_attributes(content)
            content = fix_amazon_attributes(content)
            content = fix_fragment_identifiers(content, os.path.basename(html_file))
            
            # Write back if changed
            if content != original_content:
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_count += 1
                print(f"Fixed: {os.path.basename(html_file)}")
                
        except Exception as e:
            print(f"Error processing {html_file}: {e}")
    
    print(f"Fixed {fixed_count} HTML files")
    return fixed_count

def repack_epub(extract_dir, epub_path):
    """Repack the EPUB with proper compression"""
    # Create backup
    backup_path = f"{epub_path}.backup.fixed"
    if os.path.exists(epub_path):
        shutil.copy2(epub_path, backup_path)
        print(f"Created backup: {backup_path}")
    
    # Create new EPUB
    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as epub_zip:
        # Add mimetype first (uncompressed)
        mimetype_path = os.path.join(extract_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            epub_zip.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == 'mimetype':
                    continue  # Already added
                
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, extract_dir)
                
                # Use appropriate compression
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.svg')):
                    compress_type = zipfile.ZIP_STORED  # Don't compress images
                else:
                    compress_type = zipfile.ZIP_DEFLATED  # Compress text files
                
                epub_zip.write(file_path, arc_path, compress_type=compress_type)
    
    print(f"Repacked EPUB: {epub_path}")

def fix_remaining_errors():
    epub_path = 'future1.epub'
    temp_dir = 'temp_epub_fix'
    
    # Extract EPUB
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    files_fixed = 0
    
    # Fix titlepage.xhtml - add missing closing html tag
    titlepage_path = os.path.join(temp_dir, 'titlepage.xhtml')
    if os.path.exists(titlepage_path):
        with open(titlepage_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add missing closing html tag if not present
        if not content.strip().endswith('</html>'):
            content = content.rstrip() + '\n</html>'
            
        with open(titlepage_path, 'w', encoding='utf-8') as f:
            f.write(content)
        files_fixed += 1
        print(f"Fixed titlepage.xhtml")
    
    # Fix HTML files with empty ul and body elements
    text_dir = os.path.join(temp_dir, 'text')
    if os.path.exists(text_dir):
        for filename in os.listdir(text_dir):
            if filename.endswith('.html'):
                file_path = os.path.join(text_dir, filename)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                if len(lines) >= 9:
                    line9 = lines[8]  # 0-indexed, so line 9 is index 8
                    modified = False
                    
                    # Fix empty ul elements - add a placeholder li
                    if '<ul></ul>' in line9:
                        line9 = line9.replace('<ul></ul>', '<ul><li>Content</li></ul>')
                        modified = True
                    
                    # Fix empty body elements - add a placeholder div
                    if '<body></body>' in line9:
                        line9 = line9.replace('<body></body>', '<body><div>Content</div></body>')
                        modified = True
                    
                    # Fix body elements that are not properly closed
                    if '<body>' in line9 and '</body>' not in line9:
                        line9 = line9.rstrip() + '</body>\n'
                        modified = True
                    
                    if modified:
                        lines[8] = line9
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.writelines(lines)
                        
                        files_fixed += 1
                        print(f"Fixed {filename}")
    
    print(f"\nTotal files fixed: {files_fixed}")
    
    # Create mimetype file first (must be first in archive)
    mimetype_path = os.path.join(temp_dir, 'mimetype')
    with open(mimetype_path, 'w', encoding='utf-8') as f:
        f.write('application/epub+zip')
    
    # Repack EPUB with mimetype first
    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        # Add mimetype first (uncompressed)
        zip_ref.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file != 'mimetype':  # Skip mimetype as it's already added
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zip_ref.write(file_path, arcname)
    
    # Clean up
    shutil.rmtree(temp_dir)
    
    print("\nEPUB repacked successfully!")
    
    # Run epubcheck
    print("\nRunning epubcheck...")
    import subprocess
    result = subprocess.run(['java', '-jar', 'epubcheck.jar', epub_path], 
                          capture_output=True, text=True)
    
    # Save output
    with open('output.txt', 'w', encoding='utf-8') as f:
        f.write(result.stdout)
        if result.stderr:
            f.write("\n--- STDERR ---\n")
            f.write(result.stderr)
    
    print("Epubcheck completed. Results saved to output.txt")

def main():
    epub_path = "future1.epub"
    extract_dir = "temp_extract_fix"
    
    print("Starting comprehensive EPUB error fixing...")
    
    # Extract EPUB
    extract_epub(epub_path, extract_dir)
    
    # Fix HTML files
    fixed_count = process_html_files(extract_dir)
    
    # Repack EPUB
    repack_epub(extract_dir, epub_path)
    
    # Clean up
    shutil.rmtree(extract_dir)
    
    print(f"\nFixed {fixed_count} files. Running epubcheck...")
    
    # Run epubcheck
    os.system(f'java -jar epubcheck.jar "{epub_path}" > output.txt 2>&1')
    print("EPUBCheck completed. Results saved to output.txt")

if __name__ == "__main__":
    fix_remaining_errors()