#!/usr/bin/env python3
"""
Simple EPUB validator
"""

import subprocess
import sys
import os

def validate_epub(epub_path):
    """Validate EPUB using epubcheck"""
    if not os.path.exists('epubcheck.jar'):
        print("❌ epubcheck.jar not found")
        return False
    
    print(f"🔍 Validating: {epub_path}")
    try:
        result = subprocess.run(
            ['java', '-jar', 'epubcheck.jar', epub_path],
            capture_output=True, text=True, cwd='.'
        )
        
        output = result.stdout + result.stderr
        error_count = output.count('ERROR(')
        warning_count = output.count('WARNING(')
        
        if error_count == 0:
            print(f"✅ Valid EPUB ({warning_count} warnings)")
            return True
        else:
            print(f"❌ {error_count} errors, {warning_count} warnings")
            return False
            
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python validate_epub.py <epub_file>")
        return
    
    epub_path = sys.argv[1]
    validate_epub(epub_path)

if __name__ == "__main__":
    main()