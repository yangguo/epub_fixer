import zipfile
import os
import re
import subprocess
from xml.etree import ElementTree as ET

def fix_fragment_identifiers():
    epub_path = 'future1.epub'
    temp_dir = 'temp_epub_fix'
    
    # Extract EPUB
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    files_fixed = 0
    
    # Fix fragment identifiers in HTML files by adding missing id attributes
    text_dir = os.path.join(temp_dir, 'text')
    if os.path.exists(text_dir):
        for filename in os.listdir(text_dir):
            if filename.endswith('.html'):
                file_path = os.path.join(text_dir, filename)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                modified = False
                
                # Add missing id attributes to common elements that might be referenced
                # Look for href="#something" patterns and ensure corresponding id="something" exists
                href_matches = re.findall(r'href="#([^"]+)"', content)
                
                for fragment_id in href_matches:
                    # Check if id already exists
                    if f'id="{fragment_id}"' not in content:
                        # Add id to the first suitable element (h1, h2, div, etc.)
                        # Try to find a heading or div near the link
                        patterns_to_try = [
                            (r'(<h[1-6][^>]*)(>)', f'\\1 id="{fragment_id}"\\2'),
                            (r'(<div[^>]*)(>)', f'\\1 id="{fragment_id}"\\2'),
                            (r'(<p[^>]*)(>)', f'\\1 id="{fragment_id}"\\2'),
                            (r'(<span[^>]*)(>)', f'\\1 id="{fragment_id}"\\2')
                        ]
                        
                        for pattern, replacement in patterns_to_try:
                            if re.search(pattern, content):
                                content = re.sub(pattern, replacement, content, count=1)
                                modified = True
                                break
                
                if modified:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    files_fixed += 1
                    print(f"Fixed fragment identifiers in {filename}")
    
    # Fix toc.ncx file by removing or fixing broken fragment references
    toc_path = os.path.join(temp_dir, 'toc.ncx')
    if os.path.exists(toc_path):
        try:
            with open(toc_path, 'r', encoding='utf-8') as f:
                toc_content = f.read()
            
            # Remove fragment identifiers from src attributes that cause errors
            # Replace src="file.html#fragment" with src="file.html" if fragment doesn't exist
            toc_content = re.sub(r'src="([^#"]+)#[^"]*"', r'src="\1"', toc_content)
            
            with open(toc_path, 'w', encoding='utf-8') as f:
                f.write(toc_content)
            
            files_fixed += 1
            print("Fixed toc.ncx fragment references")
        except Exception as e:
            print(f"Warning: Could not fix toc.ncx: {e}")
    
    # Fix content.opf file by removing broken fragment references
    opf_path = os.path.join(temp_dir, 'content.opf')
    if os.path.exists(opf_path):
        try:
            with open(opf_path, 'r', encoding='utf-8') as f:
                opf_content = f.read()
            
            # Remove fragment identifiers from href attributes in content.opf
            opf_content = re.sub(r'href="([^#"]+)#[^"]*"', r'href="\1"', opf_content)
            
            with open(opf_path, 'w', encoding='utf-8') as f:
                f.write(opf_content)
            
            files_fixed += 1
            print("Fixed content.opf fragment references")
        except Exception as e:
            print(f"Warning: Could not fix content.opf: {e}")
    
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
    import shutil
    shutil.rmtree(temp_dir)
    
    print("\nEPUB repacked successfully!")
    
    # Run epubcheck
    print("\nRunning epubcheck...")
    result = subprocess.run(['java', '-jar', 'epubcheck.jar', epub_path], 
                          capture_output=True, text=True)
    
    # Save output
    with open('output.txt', 'w', encoding='utf-8') as f:
        f.write(result.stdout)
        if result.stderr:
            f.write("\n--- STDERR ---\n")
            f.write(result.stderr)
    
    print("Epubcheck completed. Results saved to output.txt")

if __name__ == "__main__":
    fix_fragment_identifiers()