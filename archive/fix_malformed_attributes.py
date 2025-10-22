#!/usr/bin/env python3
"""
Fix malformed attributes and HTML structure in EPUB files
"""

import zipfile
import os
import re
import subprocess
from pathlib import Path

def fix_malformed_attributes():
    epub_path = "future1.epub"
    extract_dir = "epub_temp"
    
    print("Extracting EPUB...")
    # Extract EPUB
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # Find all HTML files
    html_files = []
    text_dir = os.path.join(extract_dir, "text")
    if os.path.exists(text_dir):
        for file in os.listdir(text_dir):
            if file.endswith(".html"):
                html_files.append(os.path.join(text_dir, file))
    
    # Also check for titlepage.xhtml
    titlepage_path = os.path.join(extract_dir, "titlepage.xhtml")
    if os.path.exists(titlepage_path):
        html_files.append(titlepage_path)
    
    print(f"Found {len(html_files)} HTML files to process")
    
    fixed_count = 0
    
    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix malformed class attributes with "> pattern
            content = re.sub(r'class=">', 'class="">', content)
            
            # Fix malformed href attributes with "><div class="> pattern
            content = re.sub(r'href="#"><div class=">', 'href="#"><div class="">', content)
            
            # Fix corrupted attribute names like hrefass=">
            content = re.sub(r'hrefass=">', 'href="#">', content)
            
            # Fix any attribute="> patterns (generic fix)
            content = re.sub(r'(\w+)=">', r'\1="">', content)
            
            # Fix missing closing quotes in attributes
            content = re.sub(r'(\w+)="([^"]*)<', r'\1="\2"<', content)
            
            # Fix malformed div tags that are not properly closed
            content = re.sub(r'<div\s+class=""[^>]*(?!>)', '<div class="">', content)
            
            # Fix nested div/a structure issues
            content = re.sub(r'><div class="">', '>', content)
            
            # Fix multiple consecutive closing tags
            content = re.sub(r'(</div>){10,}', '</div>', content)
            content = re.sub(r'(</li>){5,}', '</li>', content)
            
            # Fix malformed li structure
            content = re.sub(r'<li class="">', '<li>', content)
            
            # Fix href attributes that are malformed
            content = re.sub(r'href="#"[^>]*>', 'href="#">', content)
            
            # Ensure proper tag closure
            content = re.sub(r'<(\w+)\s+[^>]*(?<!>)$', r'<\1>', content, flags=re.MULTILINE)
            
            # Fix text content that appears outside proper tags
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if i == 8:  # Line 9 (0-indexed)
                    # Wrap any loose text in proper paragraph tags
                    if line.strip() and not line.strip().startswith('<') and not line.strip().endswith('>'):
                        lines[i] = f'<p>{line.strip()}</p>'
                    # Fix the specific malformed structure on line 9
                    if 'class=">' in line:
                        # Rebuild the line with proper structure
                        line = re.sub(r'<li class=""><a href="#"><div class="">([^<]+)</a></li>', r'<li><a href="#">\1</a></li>', line)
                        line = re.sub(r'<div class=""><li', r'<li', line)
                        lines[i] = line
            
            content = '\n'.join(lines)
            
            if content != original_content:
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_count += 1
                print(f"Fixed: {os.path.basename(html_file)}")
        
        except Exception as e:
            print(f"Error processing {html_file}: {e}")
    
    print(f"\nFixed {fixed_count} files")
    
    # Repack EPUB
    print("\nRepacking EPUB...")
    if os.path.exists(epub_path):
        os.remove(epub_path)
    
    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, extract_dir)
                zipf.write(file_path, arcname)
    
    # Clean up
    import shutil
    shutil.rmtree(extract_dir)
    
    print("EPUB repacked successfully")
    
    # Run epubcheck
    print("\nRunning epubcheck...")
    try:
        result = subprocess.run(
            ["java", "-jar", "epubcheck.jar", epub_path],
            capture_output=True,
            text=True,
            cwd="."
        )
        
        # Save output to file
        with open("output.txt", "w", encoding="utf-8") as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n--- STDERR ---\n")
                f.write(result.stderr)
        
        print("EPUBCheck completed")
        
    except Exception as e:
        print(f"Error running epubcheck: {e}")

if __name__ == "__main__":
    fix_malformed_attributes()