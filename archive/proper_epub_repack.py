#!/usr/bin/env python3
"""
Proper EPUB Repacking Script
Ensures mimetype file is first and uncompressed as required by EPUB specification.
"""

import os
import zipfile
from pathlib import Path

def repack_epub_properly(extract_dir, output_epub):
    """Repack EPUB with proper mimetype handling."""
    print(f"Repacking EPUB from {extract_dir} to {output_epub}...")
    
    # Remove existing EPUB if it exists
    if os.path.exists(output_epub):
        os.remove(output_epub)
    
    with zipfile.ZipFile(output_epub, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        # First, add mimetype file uncompressed and first
        mimetype_path = os.path.join(extract_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            zip_ref.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
            print("Added mimetype file (uncompressed, first)")
        
        # Then add all other files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == 'mimetype':  # Skip mimetype as it's already added
                    continue
                    
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, extract_dir)
                
                # Use appropriate compression
                if file.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    # Images are already compressed
                    zip_ref.write(file_path, arc_path, compress_type=zipfile.ZIP_STORED)
                else:
                    # Compress text files
                    zip_ref.write(file_path, arc_path, compress_type=zipfile.ZIP_DEFLATED)
    
    print(f"EPUB repacked successfully: {output_epub}")

def main():
    extract_dir = "temp_extract"
    output_epub = "future1.epub"
    
    if not os.path.exists(extract_dir):
        print(f"Extract directory {extract_dir} not found!")
        return
    
    # Create backup of current EPUB
    if os.path.exists(output_epub):
        backup_path = f"{output_epub}.backup.repack"
        if os.path.exists(backup_path):
            os.remove(backup_path)
        os.rename(output_epub, backup_path)
        print(f"Backup created: {backup_path}")
    
    # Repack EPUB properly
    repack_epub_properly(extract_dir, output_epub)
    
    # Run validation
    print("\nRunning epubcheck to verify...")
    os.system(f'java -jar epubcheck.jar "{output_epub}" > output.txt 2>&1')
    print("Check output.txt for validation results.")

if __name__ == "__main__":
    main()