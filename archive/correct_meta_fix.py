#!/usr/bin/env python3
"""
Correct meta tag fix for EPUB validation
"""

import os
import re
import zipfile
import subprocess
from pathlib import Path

def fix_meta_tags_properly(content):
    """
    Fix meta tags with proper XML syntax
    """
    fixes = 0
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        original_line = line
        
        # Fix meta tags that are not properly self-closed
        if '<meta' in line and not line.strip().endswith('/>'):
            # Pattern 1: Fix Content-Type meta tags
            if 'Content-Type' in line and 'charset=' in line:
                # Replace the malformed ending with proper self-closing
                line = re.sub(r'<meta([^>]*?)>\s*', r'<meta\1 />', line)
                line = re.sub(r'<meta([^>]*?)/>\s*', r'<meta\1 />', line)
            
            # Pattern 2: Fix other meta tags that don't end with />
            elif '<meta' in line:
                # Ensure meta tag is self-closed
                if not '/>' in line:
                    line = re.sub(r'<meta([^>]*?)>\s*', r'<meta\1 />', line)
        
        # Fix any double slashes or malformed closings
        line = re.sub(r'\s+/\s+/>', ' />', line)
        line = re.sub(r'"\s+/\s+/>', '" />', line)
        
        if line != original_line:
            lines[i] = line
            fixes += 1
            print(f"Fixed line {i+1}: '{original_line.strip()}' -> '{line.strip()}'")
    
    return '\n'.join(lines), fixes

def process_epub_correctly(input_path, output_path):
    """
    Process EPUB with correct meta tag fixes
    """
    total_fixes = 0
    
    # Extract EPUB
    extract_dir = 'correct_fix_temp'
    if os.path.exists(extract_dir):
        import shutil
        shutil.rmtree(extract_dir)
    
    with zipfile.ZipFile(input_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # Process all XHTML files
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith('.xhtml'):
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    fixed_content, fixes = fix_meta_tags_properly(content)
                    
                    if fixes > 0:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(fixed_content)
                        total_fixes += fixes
                        print(f"Fixed {fixes} issues in {file}")
                
                except Exception as e:
                    print(f"Error processing {file}: {e}")
    
    # Repack EPUB
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
        # Add mimetype first (uncompressed)
        mimetype_path = os.path.join(extract_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            zip_out.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == 'mimetype':
                    continue
                
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, extract_dir)
                zip_out.write(file_path, arcname)
    
    # Clean up
    import shutil
    shutil.rmtree(extract_dir)
    
    return total_fixes

def run_epubcheck(epub_path):
    """
    Run epubcheck and return results
    """
    try:
        result = subprocess.run(
            ['java', '-jar', 'epubcheck.jar', epub_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        output = result.stdout + result.stderr
        
        # Count errors
        fatal_errors = output.count('FATAL')
        errors = output.count('ERROR') - fatal_errors
        
        return output, fatal_errors, errors
    
    except Exception as e:
        return f"Error running epubcheck: {e}", 0, 0

def main():
    input_epub = 'doing2_ultimate_fixed.epub'
    output_epub = 'doing2_correct_fixed.epub'
    validation_file = 'correct_validation.txt'
    
    if not os.path.exists(input_epub):
        print(f"Input file {input_epub} not found!")
        return
    
    print("Starting correct meta tag fix...")
    
    # Process the EPUB
    fixes_applied = process_epub_correctly(input_epub, output_epub)
    
    print(f"\nApplied {fixes_applied} fixes. Running validation...")
    
    # Validate the result
    validation_output, fatal_errors, errors = run_epubcheck(output_epub)
    
    # Save validation results
    with open(validation_file, 'w', encoding='utf-8') as f:
        f.write(validation_output)
    
    print(f"\nValidation complete:")
    print(f"Fatal errors: {fatal_errors}")
    print(f"Regular errors: {errors}")
    print(f"Results saved to {validation_file}")
    
    if fatal_errors == 0 and errors == 0:
        print("\n🎉 EPUB is now valid!")
    else:
        print(f"\n⚠️  Still has {fatal_errors} fatal errors and {errors} regular errors")

if __name__ == '__main__':
    main()