#!/usr/bin/env python3
import zipfile
import os
import re
import shutil
from pathlib import Path

def fix_malformed_html(content):
    """Fix severely malformed HTML structure"""
    
    # First, let's fix the broken body tag structure
    # Look for patterns like: <body class="calibre"><div class="toclist calibre2 contentsh" id="toc____h1_class_">calibre1">>
    content = re.sub(
        r'<body[^>]*><div[^>]*id="toc____h1_class_"[^>]*calibre1">>',
        '<body class="calibre"><div class="toclist calibre2 contentsh">',
        content
    )
    
    # Fix broken div tags with malformed attributes
    content = re.sub(
        r'<div[^>]*class="[^"]*contentsh[^"]*"[^>]*id="[^"]*h1_class_[^"]*"[^>]*>',
        '<div class="contentsh">',
        content
    )
    
    # Fix any remaining malformed div opening tags
    content = re.sub(
        r'<div[^>]*>>',
        '<div>',
        content
    )
    
    # Fix malformed h1 tags like "h1 iii" or "h1 acknowledgment"
    content = re.sub(
        r'<h1\s+(\w+)\s*>',
        r'<h1 class="\1">',
        content
    )
    
    # Fix unclosed h1 tags - add closing tag before next major element
    content = re.sub(
        r'(<h1[^>]*>[^<]*?)(<(?:div|p|h[1-6]|body|html))',
        r'\1</h1>\2',
        content
    )
    
    # Fix missing li opening tags
    content = re.sub(
        r'</li>\s*([^<]+?)\s*<a',
        r'</li><li>\1<a',
        content
    )
    
    # Count and balance div tags
    open_divs = len(re.findall(r'<div[^>]*>', content))
    close_divs = len(re.findall(r'</div>', content))
    
    if open_divs > close_divs:
        missing_closes = open_divs - close_divs
        # Add missing closing divs before </body> or </html>
        if '</body>' in content:
            content = content.replace('</body>', '</div>' * missing_closes + '</body>')
        elif '</html>' in content:
            content = content.replace('</html>', '</div>' * missing_closes + '</html>')
        else:
            content += '</div>' * missing_closes
    
    # Count and balance h1 tags
    open_h1s = len(re.findall(r'<h1[^>]*>', content))
    close_h1s = len(re.findall(r'</h1>', content))
    
    if open_h1s > close_h1s:
        missing_closes = open_h1s - close_h1s
        # Add missing closing h1s before </body> or </html>
        if '</body>' in content:
            content = content.replace('</body>', '</h1>' * missing_closes + '</body>')
        elif '</html>' in content:
            content = content.replace('</html>', '</h1>' * missing_closes + '</html>')
        else:
            content += '</h1>' * missing_closes
    
    return content

def process_epub():
    epub_path = 'future1.epub'
    
    # Create backup
    backup_path = f'{epub_path}.backup.structure'
    if os.path.exists(backup_path):
        os.remove(backup_path)
    shutil.copy2(epub_path, backup_path)
    print(f"Created backup: {backup_path}")
    
    # Extract EPUB
    extract_dir = 'temp_extract_structure'
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # Process HTML files
    text_dir = Path(extract_dir) / 'text'
    files_fixed = 0
    
    for html_file in text_dir.glob('*.html'):
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            fixed_content = fix_malformed_html(content)
            
            if fixed_content != original_content:
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                files_fixed += 1
                print(f"Fixed: {html_file.name}")
                
        except Exception as e:
            print(f"Error processing {html_file}: {e}")
    
    print(f"\nFixed {files_fixed} files")
    
    # Repack EPUB with proper mimetype ordering
    temp_epub = 'temp_future1.epub'
    if os.path.exists(temp_epub):
        os.remove(temp_epub)
    
    with zipfile.ZipFile(temp_epub, 'w', zipfile.ZIP_DEFLATED) as zip_out:
        # Add mimetype first (uncompressed)
        mimetype_path = Path(extract_dir) / 'mimetype'
        if mimetype_path.exists():
            zip_out.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == 'mimetype':
                    continue
                file_path = Path(root) / file
                arcname = file_path.relative_to(extract_dir)
                zip_out.write(file_path, arcname)
    
    # Replace original
    os.replace(temp_epub, epub_path)
    
    # Cleanup
    shutil.rmtree(extract_dir)
    
    print("\nEPUB repacked successfully")
    
    # Run epubcheck
    print("\nRunning epubcheck...")
    os.system('java -jar epubcheck.jar future1.epub > output.txt 2>&1')
    print("Epubcheck completed. Results saved to output.txt")

if __name__ == "__main__":
    process_epub()