#!/usr/bin/env python3
"""
Comprehensive EPUB Fixing Script

This script uses the comprehensive fixing functionality from fix_epub.py
to apply all available fixes to an EPUB file.

Usage:
    python fix_epub_comprehensive.py <epub_file>

Example:
    python fix_epub_comprehensive.py climate1.epub
"""

import sys
import os
import tempfile
from fix_epub import extract_epub, repack_epub, fix_epub_comprehensive

def main():
    if len(sys.argv) != 2:
        print("Usage: python fix_epub_comprehensive.py <epub_file>")
        sys.exit(1)
    
    epub_file = sys.argv[1]
    
    if not os.path.exists(epub_file):
        print(f"Error: {epub_file} not found")
        sys.exit(1)
    
    print(f"Starting comprehensive EPUB fixing for: {epub_file}")
    
    # Create temporary directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        extract_dir = os.path.join(temp_dir, 'epub_extracted')
        
        # Extract EPUB
        print("Extracting EPUB...")
        if not extract_epub(epub_file, extract_dir):
            print("Failed to extract EPUB")
            sys.exit(1)
        
        # Apply comprehensive fixes
        print("Applying comprehensive fixes...")
        fixed_files = fix_epub_comprehensive(extract_dir)
        
        if fixed_files:
            print(f"\nFixed {len(fixed_files)} files:")
            for file_path in fixed_files:
                print(f"  - {os.path.basename(file_path)}")
            
            # Create backup of original
            backup_file = epub_file.replace('.epub', '_backup.epub')
            if os.path.exists(backup_file):
                os.remove(backup_file)
            os.rename(epub_file, backup_file)
            print(f"\nCreated backup: {backup_file}")
            
            # Repack EPUB
            print("Repacking EPUB...")
            if repack_epub(extract_dir, epub_file):
                print(f"\nSuccessfully fixed and repacked: {epub_file}")
                print("\nRun epubcheck to verify the fixes:")
                print(f"java -jar epubcheck.jar {epub_file}")
            else:
                print("Failed to repack EPUB")
                # Restore backup
                os.rename(backup_file, epub_file)
                sys.exit(1)
        else:
            print("\nNo fixes were needed - EPUB is already in good condition.")

if __name__ == '__main__':
    main()