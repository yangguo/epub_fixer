#!/usr/bin/env python3
import zipfile
import os
import re
import shutil
import subprocess
from pathlib import Path

def extract_epub(epub_path, extract_dir):
    """Extract EPUB to directory"""
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print(f"Extracted EPUB to {extract_dir}")

def fix_xml_spaces(content):
    """Fix XML syntax by removing extra spaces before closing tags"""
    # Remove spaces before > in opening tags
    content = re.sub(r'\s+>', '>', content)
    
    # Remove spaces before /> in self-closing tags
    content = re.sub(r'\s+/>', ' />', content)
    
    # Fix specific patterns that cause XML parsing errors
    # Remove extra spaces in tag names
    content = re.sub(r'<(\w+)\s+([^>]*?)>', r'<\1 \2>', content)
    
    # Clean up multiple spaces in attributes
    content = re.sub(r'\s+', ' ', content)
    
    # Fix malformed attributes with extra spaces
    content = re.sub(r'="([^"]*?)"\s+>', r'="\1">', content)
    
    # Ensure proper spacing in attributes
    content = re.sub(r'(\w+)="([^"]*?)"(\w)', r'\1="\2" \3', content)
    
    return content

def process_html_files(extract_dir):
    """Process all HTML files to fix XML spaces"""
    html_files = []
    text_dir = os.path.join(extract_dir, 'text')
    
    # Find all HTML files
    if os.path.exists(text_dir):
        for file in os.listdir(text_dir):
            if file.endswith('.html'):
                html_files.append(os.path.join(text_dir, file))
    
    # Also check for titlepage.xhtml
    titlepage_path = os.path.join(extract_dir, 'titlepage.xhtml')
    if os.path.exists(titlepage_path):
        html_files.append(titlepage_path)
    
    fixed_files = 0
    
    for file_path in html_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            fixed_content = fix_xml_spaces(content)
            
            if fixed_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                fixed_files += 1
                print(f"Fixed XML spaces in {os.path.basename(file_path)}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    print(f"Fixed XML spaces in {fixed_files} files")
    return fixed_files

def repack_epub(extract_dir, output_path):
    """Repack the EPUB with proper compression"""
    # Create backup
    if os.path.exists(output_path):
        backup_path = output_path.replace('.epub', '_backup.epub')
        shutil.copy2(output_path, backup_path)
        print(f"Created backup: {backup_path}")
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
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
                arcname = os.path.relpath(file_path, extract_dir)
                zip_ref.write(file_path, arcname)
    
    print(f"Repacked EPUB: {output_path}")

def main():
    epub_path = 'future1.epub'
    extract_dir = 'epub_temp'
    
    if not os.path.exists(epub_path):
        print(f"Error: {epub_path} not found")
        return
    
    # Extract EPUB
    extract_epub(epub_path, extract_dir)
    
    # Fix XML spaces
    fixed_files = process_html_files(extract_dir)
    
    # Repack EPUB
    repack_epub(extract_dir, epub_path)
    
    # Clean up
    shutil.rmtree(extract_dir)
    
    # Run epubcheck
    print("\nRunning epubcheck...")
    try:
        result = subprocess.run(['java', '-jar', 'epubcheck.jar', epub_path], 
                              capture_output=True, text=True, cwd='.')
        
        with open('output.txt', 'w', encoding='utf-8') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n--- STDERR ---\n")
                f.write(result.stderr)
        
        print("EPUBCheck completed")
        
    except Exception as e:
        print(f"Error running epubcheck: {e}")

if __name__ == "__main__":
    main()