#!/usr/bin/env python3
import zipfile
import os
import re
import tempfile
import shutil
import subprocess
from pathlib import Path

def fix_html_structure(content):
    """Fix malformed HTML structure issues"""
    
    # Fix malformed list items - add missing <li> tags
    content = re.sub(r'</li>\s+class="([^"]+)"><a', r'</li>\n<li class="\1"><a', content)
    
    # Fix malformed h1 tags (like h1 iii or h1 acknowledgment)
    content = re.sub(r'<h1\s+([a-zA-Z]+)\s*(?![>=])', r'<h1 class="\1">', content)
    
    # Fix missing closing h1 tags
    content = re.sub(r'<h1([^>]*)>([^<]*?)(?=\s*<(?!/))', r'<h1\1>\2</h1>\n<', content)
    
    # Fix div tags that are not properly closed
    # First, let's fix malformed div openings
    content = re.sub(r'<div([^>]*?)(?<!>)\s*(?=[^>]*[a-zA-Z][^>]*$)', r'<div\1>', content, flags=re.MULTILINE)
    
    # Count and balance div tags
    open_divs = len(re.findall(r'<div[^>]*>', content))
    close_divs = len(re.findall(r'</div>', content))
    
    missing_closes = open_divs - close_divs
    
    if missing_closes > 0:
        # Add missing closing div tags before </body>
        body_end_match = re.search(r'</body>', content)
        if body_end_match:
            closing_divs = '\n'.join(['</div>'] * missing_closes)
            insert_pos = body_end_match.start()
            content = content[:insert_pos] + closing_divs + '\n' + content[insert_pos:]
        else:
            # If no </body> tag, add before </html>
            html_end_match = re.search(r'</html>', content)
            if html_end_match:
                closing_divs = '\n'.join(['</div>'] * missing_closes)
                insert_pos = html_end_match.start()
                content = content[:insert_pos] + closing_divs + '\n' + content[insert_pos:]
    
    # Fix missing closing h1 tags more aggressively
    content = re.sub(r'<h1([^>]*)>([^<]*?)(?=\s*(?:</body>|</div>|</html>|$))', r'<h1\1>\2</h1>', content)
    
    return content

def process_epub(epub_path):
    """Process EPUB file to fix HTML structure issues"""
    
    # Create backup
    backup_path = epub_path.replace('.epub', '_backup_structure.epub')
    shutil.copy2(epub_path, backup_path)
    print(f"Created backup: {backup_path}")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract EPUB
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Find and process HTML files
        html_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(('.html', '.xhtml')):
                    html_files.append(os.path.join(root, file))
        
        files_fixed = 0
        
        for html_file in html_files:
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                fixed_content = fix_html_structure(content)
                
                if fixed_content != original_content:
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)
                    files_fixed += 1
                    print(f"Fixed: {os.path.basename(html_file)}")
                    
            except Exception as e:
                print(f"Error processing {html_file}: {e}")
        
        print(f"\nFixed {files_fixed} files")
        
        # Repack EPUB with proper mimetype ordering
        with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            # Add mimetype first (uncompressed)
            mimetype_path = os.path.join(temp_dir, 'mimetype')
            if os.path.exists(mimetype_path):
                zip_ref.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
            
            # Add all other files
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file == 'mimetype':
                        continue  # Already added
                    
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, temp_dir)
                    zip_ref.write(file_path, arc_path)
        
        print(f"Repacked EPUB: {epub_path}")

def main():
    epub_path = 'future1.epub'
    
    if not os.path.exists(epub_path):
        print(f"Error: {epub_path} not found")
        return
    
    print("Starting HTML structure fix...")
    process_epub(epub_path)
    
    # Run epubcheck
    print("\nRunning epubcheck...")
    try:
        result = subprocess.run(
            ['java', '-jar', 'epubcheck.jar', epub_path],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # Save output to file
        with open('output.txt', 'w', encoding='utf-8') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n--- STDERR ---\n")
                f.write(result.stderr)
        
        print("Epubcheck completed. Results saved to output.txt")
        
    except subprocess.TimeoutExpired:
        print("Epubcheck timed out")
    except Exception as e:
        print(f"Error running epubcheck: {e}")

if __name__ == "__main__":
    main()