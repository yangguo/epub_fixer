#!/usr/bin/env python3
"""Simple EPUB validation script"""

import os
import sys

from config import EPUBCHECK_JAR
from utils import count_errors, run_epubcheck


def main():
    """Main function"""
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <epub_file>")
        sys.exit(1)
    
    epub_path = sys.argv[1]
    if not os.path.exists(epub_path):
        print(f"Error: File not found - {epub_path}")
        sys.exit(1)
    
    if not os.path.exists(EPUBCHECK_JAR):
        print(f"Error: epubcheck.jar not found at {EPUBCHECK_JAR}")
        sys.exit(1)
    
    print(f"Validating: {epub_path}")
    print("=" * 60)
    
    output = run_epubcheck(epub_path)
    
    # Count errors and warnings
    error_count, warning_count = count_errors(output)
    
    print(output)
    print("=" * 60)
    
    if error_count == 0:
        print(f"✓ SUCCESS: No errors found (Warnings: {warning_count})")
        sys.exit(0)
    else:
        print(f"✗ FAILURE: {error_count} errors, {warning_count} warnings found")
        sys.exit(1)

if __name__ == "__main__":
    main()
