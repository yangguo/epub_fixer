#!/usr/bin/env python3
import zipfile
import os
import re
import shutil
from pathlib import Path

def fix_malformed_html(content):
    """Fix specific malformed HTML structures found in the EPUB"""
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        original_line = line
        
        # Fix the massive malformed line 9 structure
        if i == 8 and len(line) > 1000:  # This is likely the problematic line 9
            print(f"Processing long line {i+1} with {len(line)} characters")
            
            # Fix missing <li> tags before class="contentsh"
            line = re.sub(r'(?<!<li>)\s+class="contentsh"', r'<li class="contentsh"', line)
            
            # Fix missing <div> tags before class="calibre2"
            line = re.sub(r'(?<!<div>)\s+class="calibre2"', r'<div class="calibre2"', line)
            
            # Fix stray </li></li> patterns
            line = re.sub(r'</li></li>', r'</li>', line)
            
            # Ensure proper structure for table of contents entries
            # Pattern: class="contentsh"><a href="#" class="calibre3">Text</a></li>
            line = re.sub(
                r'<li class="contentsh"><a href="([^"]+)" class="([^"]+)">([^<]+)</a></li>',
                r'<li class="contentsh"><a href="\1" class="\2">\3</a></li>',
                line
            )
            
            # Fix any remaining orphaned class attributes
            line = re.sub(r'\s+class="([^"]+)">(?!<)', r'<div class="\1">', line)
            
            # Balance any unmatched tags
            div_count = line.count('<div') - line.count('</div>')
            li_count = line.count('<li') - line.count('</li>')
            
            if div_count > 0 or li_count > 0:
                closing_tags = '</div>' * div_count + '</li>' * li_count
                if '</body>' in line:
                    line = line.replace('</body>', f'{closing_tags}</body>')
                else:
                    line = line.rstrip() + closing_tags
            
            print(f"Fixed massive malformed structure in line {i+1}")
        
        # Fix malformed h1 patterns like "h1 iii" -> "<h1>iii</h1>"
        elif re.search(r'\bh1\s+\w+', line) and '<h1' not in line:
            line = re.sub(r'\bh1\s+(\w+)', r'<h1>\1</h1>', line)
            print(f"Fixed malformed h1 in line {i+1}")
        
        # Fix simple unclosed div tags
        elif '<div' in line and not line.count('<div') == line.count('</div>'):
            div_opens = line.count('<div')
            div_closes = line.count('</div>')
            missing_closes = div_opens - div_closes
            
            if missing_closes > 0:
                closing_divs = '</div>' * missing_closes
                if '</body>' in line:
                    line = line.replace('</body>', f'{closing_divs}</body>')
                elif '</html>' in line:
                    line = line.replace('</html>', f'{closing_divs}</html>')
                else:
                    line = line.rstrip() + closing_divs
                print(f"Added {missing_closes} missing </div> in line {i+1}")
        
        # Fix simple unclosed h1 tags
        elif '<h1' in line and not line.count('<h1') == line.count('</h1>'):
            h1_opens = line.count('<h1')
            h1_closes = line.count('</h1>')
            missing_closes = h1_opens - h1_closes
            
            if missing_closes > 0:
                closing_h1s = '</h1>' * missing_closes
                if '</body>' in line:
                    line = line.replace('</body>', f'{closing_h1s}</body>')
                elif '</html>' in line:
                    line = line.replace('</html>', f'{closing_h1s}</html>')
                else:
                    line = line.rstrip() + closing_h1s
                print(f"Added {missing_closes} missing </h1> in line {i+1}")
        
        if line != original_line:
            print(f"  Line {i+1} changed from {len(original_line)} to {len(line)} characters")
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def process_epub(epub_path):
    """Process the EPUB file to fix HTML structure issues"""
    # Create backup
    backup_path = epub_path.replace('.epub', '_backup.epub')
    if not os.path.exists(backup_path):
        shutil.copy2(epub_path, backup_path)
        print(f"Created backup: {backup_path}")
    
    # Extract EPUB
    extract_dir = 'temp_epub_extract'
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # Process HTML files
    text_dir = os.path.join(extract_dir, 'text')
    files_fixed = 0
    
    if os.path.exists(text_dir):
        for filename in os.listdir(text_dir):
            if filename.endswith('.html'):
                file_path = os.path.join(text_dir, filename)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                
                fixed_content = fix_malformed_html(original_content)
                
                if fixed_content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)
                    files_fixed += 1
                    print(f"Fixed: {filename}")
    
    print(f"Total files fixed: {files_fixed}")
    
    # Repack EPUB with correct mimetype ordering
    if os.path.exists(epub_path):
        os.remove(epub_path)
    
    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        # Add mimetype first (uncompressed)
        mimetype_path = os.path.join(extract_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            zip_ref.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file != 'mimetype':  # Skip mimetype as it's already added
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, extract_dir)
                    zip_ref.write(file_path, arcname)
    
    # Cleanup
    shutil.rmtree(extract_dir)
    print(f"Repacked EPUB: {epub_path}")

if __name__ == "__main__":
    epub_file = "future1.epub"
    
    if not os.path.exists(epub_file):
        print(f"Error: {epub_file} not found!")
        exit(1)
    
    print(f"Processing {epub_file}...")
    process_epub(epub_file)
    
    # Run epubcheck
    print("\nRunning epubcheck...")
    result = os.system(f'java -jar epubcheck.jar "{epub_file}" > output.txt 2>&1')
    print(f"EPUBCheck completed with exit code: {result}")
    print("Results saved to output.txt")