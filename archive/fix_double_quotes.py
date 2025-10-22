import zipfile
import os
import re
from pathlib import Path

def fix_double_quotes_in_epub(epub_path):
    # Create backup
    backup_path = f"{epub_path}.backup.double_quotes"
    if os.path.exists(backup_path):
        os.remove(backup_path)
    os.rename(epub_path, backup_path)
    
    # Extract EPUB
    extract_dir = "temp_fix_quotes"
    if os.path.exists(extract_dir):
        import shutil
        shutil.rmtree(extract_dir)
    
    with zipfile.ZipFile(backup_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # Fix double quotes in charset attributes
    text_dir = os.path.join(extract_dir, 'text')
    files_fixed = 0
    
    if os.path.exists(text_dir):
        for html_file in os.listdir(text_dir):
            if html_file.endswith('.html'):
                file_path = os.path.join(text_dir, html_file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Fix the specific double quote issue in charset
                original_content = content
                content = content.replace('charset=""utf-8"', 'charset="utf-8"')
                content = content.replace('charset="utf-8""', 'charset="utf-8"')
                
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    files_fixed += 1
                    print(f"Fixed double quotes in {html_file}")
    
    # Also check titlepage.xhtml
    titlepage_path = os.path.join(extract_dir, 'titlepage.xhtml')
    if os.path.exists(titlepage_path):
        with open(titlepage_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        content = content.replace('charset=""utf-8"', 'charset="utf-8"')
        content = content.replace('charset="utf-8""', 'charset="utf-8"')
        
        if content != original_content:
            with open(titlepage_path, 'w', encoding='utf-8') as f:
                f.write(content)
            files_fixed += 1
            print(f"Fixed double quotes in titlepage.xhtml")
    
    print(f"Fixed double quotes in {files_fixed} files")
    
    # Repack EPUB with proper mimetype handling
    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as epub_zip:
        # Add mimetype first, uncompressed
        mimetype_path = os.path.join(extract_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            epub_zip.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == 'mimetype':
                    continue  # Already added
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, extract_dir)
                
                # Use appropriate compression
                if file.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    compress_type = zipfile.ZIP_STORED
                else:
                    compress_type = zipfile.ZIP_DEFLATED
                
                epub_zip.write(file_path, arcname, compress_type=compress_type)
    
    print(f"Repacked EPUB: {epub_path}")
    
    # Clean up
    import shutil
    shutil.rmtree(extract_dir)
    
    return files_fixed

if __name__ == "__main__":
    epub_file = "future1.epub"
    files_fixed = fix_double_quotes_in_epub(epub_file)
    print(f"\nTotal files fixed: {files_fixed}")
    
    # Run epubcheck
    print("\nRunning epubcheck...")
    os.system("java -jar epubcheck.jar future1.epub > output.txt 2>&1")
    print("EPUBCheck completed. Check output.txt for results.")