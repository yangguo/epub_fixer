#!/usr/bin/env python3
"""
Quick validation script to check if the EPUB is now valid
"""

import subprocess
import sys
import os

def validate_epub(epub_file):
    """Validate EPUB using epubcheck"""
    if not os.path.exists(epub_file):
        print(f"❌ EPUB file not found: {epub_file}")
        return False
    
    if not os.path.exists('epubcheck.jar'):
        print("❌ epubcheck.jar not found")
        return False
    
    try:
        # Run epubcheck
        result = subprocess.run(
            ['java', '-jar', 'epubcheck.jar', epub_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout + result.stderr
        
        # Count errors and warnings
        error_count = output.count('ERROR(')
        warning_count = output.count('WARNING(')
        
        print(f"📊 Validation Results for {epub_file}:")
        print(f"   Errors: {error_count}")
        print(f"   Warnings: {warning_count}")
        
        if error_count == 0:
            print("✅ EPUB is valid!")
            return True
        else:
            print("❌ EPUB has errors")
            # Show first few errors
            lines = output.split('\n')
            error_lines = [line for line in lines if 'ERROR(' in line][:5]
            if error_lines:
                print("First few errors:")
                for error in error_lines:
                    print(f"   {error}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Validation timed out")
        return False
    except Exception as e:
        print(f"❌ Error running validation: {e}")
        return False

if __name__ == '__main__':
    epub_file = sys.argv[1] if len(sys.argv) > 1 else 'doing1.epub'
    success = validate_epub(epub_file)
    sys.exit(0 if success else 1)