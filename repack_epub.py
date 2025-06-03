#!/usr/bin/env python3
import zipfile
import os
import sys
from pathlib import Path

def repack_epub(work_dir, output_epub):
    """Repack EPUB with mimetype as first entry (uncompressed)"""
    work_dir = Path(work_dir)
    
    if not work_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {work_dir}")
    
    with zipfile.ZipFile(output_epub, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add mimetype first (uncompressed)
        mimetype_path = work_dir / 'mimetype'
        if mimetype_path.exists():
            zipf.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
            print(f"Added mimetype as first entry (uncompressed)")
        else:
            print("Warning: No mimetype file found")
        
        # Add all other files
        file_count = 0
        for root, dirs, files in os.walk(work_dir):
            for file in files:
                if file == 'mimetype':
                    continue  # Already added
                file_path = Path(root) / file
                arcname = str(file_path.relative_to(work_dir)).replace('\\', '/')
                zipf.write(file_path, arcname)
                file_count += 1
                
    print(f"EPUB repacked successfully as {output_epub} ({file_count + 1} files)")

def main():
    """Main function to handle command line usage."""
    if len(sys.argv) < 3:
        print("Usage: python repack_epub.py <source_directory> <output_epub>")
        print("")
        print("Examples:")
        print("  python repack_epub.py extracted_epub/ output.epub")
        print("  python repack_epub.py book_unpacked book_repacked.epub")
        print("")
        print("This script repacks an extracted EPUB directory into a proper EPUB file.")
        print("The mimetype file will be added first and uncompressed as required by EPUB spec.")
        sys.exit(1)
    
    source_dir = sys.argv[1]
    output_file = sys.argv[2]
    
    try:
        repack_epub(source_dir, output_file)
        print(f"\nSuccess! EPUB created: {output_file}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()