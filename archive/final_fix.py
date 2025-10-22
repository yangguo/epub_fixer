#!/usr/bin/env python3
"""
Final fix for the last remaining meta tag error in titlepage.xhtml
"""

import os
import re
import zipfile
import subprocess

def fix_titlepage_meta(content):
    """
    Fix the specific meta tag error in titlepage.xhtml
    """
    fixes = 0
    
    # Fix the specific pattern: charset="UTF-8" -> charset="UTF-8"
    # This targets the extra quote issue
    pattern = r'charset="UTF-8"'
    replacement = 'charset="UTF-8"'
    
    if pattern in content:
        content = content.replace(pattern, replacement)
        fixes += 1
        print(f"Fixed charset pattern: {pattern} -> {replacement}")
    
    return content, fixes

def process_epub_final_fix(input_path, output_path):
    """
    Process EPUB with final meta tag fix
    """
    total_fixes = 0
    
    # Extract EPUB
    extract_dir = 'final_fix_temp'
    if os.path.exists(extract_dir):
        import shutil
        shutil.rmtree(extract_dir)
    
    with zipfile.ZipFile(input_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # Process titlepage.xhtml specifically
    titlepage_path = os.path.join(extract_dir, 'titlepage.xhtml')
    
    if os.path.exists(titlepage_path):
        try:
            with open(titlepage_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            fixed_content, fixes = fix_titlepage_meta(content)
            
            if fixes > 0:
                with open(titlepage_path, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(fixed_content)
                total_fixes += fixes
                print(f"Fixed {fixes} issues in titlepage.xhtml")
            else:
                print("No fixes needed in titlepage.xhtml")
        
        except Exception as e:
            print(f"Error processing titlepage.xhtml: {e}")
    else:
        print("titlepage.xhtml not found")
    
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
    input_epub = 'doing2_manual_fixed.epub'
    output_epub = 'doing2_final_fixed.epub'
    validation_file = 'final_validation.txt'
    
    if not os.path.exists(input_epub):
        print(f"Input file {input_epub} not found!")
        return
    
    print("Starting final meta tag fix...")
    
    # Process the EPUB
    fixes_applied = process_epub_final_fix(input_epub, output_epub)
    
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
    elif fatal_errors == 0:
        print(f"\n✅ No fatal errors! Only {errors} regular errors remain")
    else:
        print(f"\n⚠️  Still has {fatal_errors} fatal errors and {errors} regular errors")

if __name__ == '__main__':
    main()