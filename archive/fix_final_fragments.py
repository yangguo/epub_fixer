import zipfile
import os
import re
import subprocess

def fix_final_fragments():
    epub_path = 'future1.epub'
    temp_dir = 'temp_epub_fix'
    
    # Extract EPUB
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    files_fixed = 0
    
    # Fix the remaining fragment identifier issues
    text_dir = os.path.join(temp_dir, 'text')
    if os.path.exists(text_dir):
        for filename in os.listdir(text_dir):
            if filename.endswith('.html'):
                file_path = os.path.join(text_dir, filename)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # For part0000_split_000.html, fix the specific line 9 issue
                if filename == 'part0000_split_000.html':
                    # Replace the problematic href links with valid ones or remove fragments
                    # Option 1: Remove the fragment identifiers that don't exist
                    content = content.replace('href="#dedication"', 'href="#"')
                    content = content.replace('href="#title"', 'href="#"')
                    
                    # Option 2: Or we could add the missing elements with proper ids
                    # Let's add them to the body if they don't exist
                    if 'id="dedication"' not in content:
                        # Add a hidden dedication element
                        content = content.replace('</body>', '<div id="dedication" style="display:none;"></div></body>')
                    
                    if 'id="title"' not in content:
                        # Add a hidden title element
                        content = content.replace('</body>', '<div id="title" style="display:none;"></div></body>')
                
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    files_fixed += 1
                    print(f"Fixed final fragments in {filename}")
    
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
    fix_final_fragments()