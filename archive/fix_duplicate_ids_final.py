import zipfile
import os
import re
import subprocess

def fix_duplicate_ids():
    epub_path = 'future1.epub'
    temp_dir = 'temp_epub_fix'
    
    # Extract EPUB
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    files_fixed = 0
    
    # Fix duplicate id attributes in HTML files
    text_dir = os.path.join(temp_dir, 'text')
    if os.path.exists(text_dir):
        for filename in os.listdir(text_dir):
            if filename.endswith('.html'):
                file_path = os.path.join(text_dir, filename)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Find and fix duplicate id attributes in the same element
                # Pattern: element with multiple id attributes
                def fix_duplicate_ids_in_element(match):
                    element = match.group(0)
                    # Extract all id values
                    id_matches = re.findall(r'id="([^"]+)"', element)
                    if len(id_matches) > 1:
                        # Keep only the first id, remove duplicates
                        first_id = id_matches[0]
                        # Remove all id attributes
                        element_no_ids = re.sub(r'\s+id="[^"]+"', '', element)
                        # Add back only the first id
                        element_no_ids = element_no_ids.replace('>', f' id="{first_id}">', 1)
                        return element_no_ids
                    return element
                
                # Fix duplicate ids in any HTML element
                content = re.sub(r'<[^>]*id="[^"]+"[^>]*id="[^"]+"[^>]*>', fix_duplicate_ids_in_element, content)
                
                # Also handle cases where there might be more than 2 ids
                # Keep applying the fix until no more duplicates
                max_iterations = 10
                iteration = 0
                while iteration < max_iterations:
                    new_content = re.sub(r'<[^>]*id="[^"]+"[^>]*id="[^"]+"[^>]*>', fix_duplicate_ids_in_element, content)
                    if new_content == content:
                        break
                    content = new_content
                    iteration += 1
                
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    files_fixed += 1
                    print(f"Fixed duplicate ids in {filename}")
    
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
    fix_duplicate_ids()