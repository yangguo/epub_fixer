#!/usr/bin/env python3
"""Simple EPUB validation script"""

import sys
import os
import zipfile

from utils import run_epubcheck, count_errors, find_unclosed_br_tags

def find_unclosed_br_in_epub(epub_path):
    """Return list of EPUB files containing raw <br> tags that are not self-closed."""
    bad_files = []
    with zipfile.ZipFile(epub_path, 'r') as zf:
        for name in zf.namelist():
            if not name.lower().endswith(('.xhtml', '.html', '.htm')):
                continue
            try:
                text = zf.read(name).decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = zf.read(name).decode('cp1251')
                except Exception:
                    continue
            if find_unclosed_br_tags(text):
                bad_files.append(name)
    return bad_files

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <epub_file>")
        sys.exit(1)
    
    epub_path = sys.argv[1]
    if not os.path.exists(epub_path):
        print(f"Error: File not found - {epub_path}")
        sys.exit(1)
    
    if not os.path.exists("epubcheck.jar"):
        print("Error: epubcheck.jar not found in current directory")
        sys.exit(1)
    
    print(f"Validating: {epub_path}")
    print("=" * 60)
    
    output = run_epubcheck(epub_path)
    
    # Count errors and warnings
    error_count, warning_count = count_errors(output)
    
    print(output)
    print("=" * 60)

    br_errors = find_unclosed_br_in_epub(epub_path)
    if br_errors:
        print("⚠️  Detected unclosed <br> tags in XHTML/HTML files:")
        for file_name in br_errors[:30]:
            print(f" - {file_name}")
        if len(br_errors) > 30:
            print(f"   ...and {len(br_errors) - 30} more files")
        error_count += len(br_errors)
    
    if error_count == 0:
        print(f"✓ SUCCESS: No errors found (Warnings: {warning_count})")
        sys.exit(0)
    else:
        print(f"✗ FAILURE: {error_count} errors, {warning_count} warnings found")
        sys.exit(1)

if __name__ == "__main__":
    main()
