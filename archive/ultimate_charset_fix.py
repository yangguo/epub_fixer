#!/usr/bin/env python3
import os
import zipfile
import tempfile
import shutil
import subprocess
import re

def fix_charset_quotes(content):
    """
    Fix the specific charset quote issue: charset="UTF-8" -> charset="UTF-8"
    """
    fixes_applied = 0
    
    # Pattern to match charset="UTF-8" (with extra quote before UTF-8)
    pattern = r'charset=""UTF-8"'
    replacement = r'charset="UTF-8"'
    
    new_content, count = re.subn(pattern, replacement, content)
    fixes_applied += count
    
    if count > 0:
        print(f"Fixed {count} charset quote issues (UTF-8)")
    
    # Also handle lowercase utf-8
    pattern2 = r'charset=""utf-8"'
    replacement2 = r'charset="utf-8"'
    
    new_content, count2 = re.subn(pattern2, replacement2, new_content)
    fixes_applied += count2
    
    if count2 > 0:
        print(f"Fixed {count2} charset quote issues (utf-8)")
    
    return new_content, fixes_applied

def process_epub(epub_path, output_path):
    """
    Process EPUB file to fix charset issues
    """
    total_fixes = 0
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract EPUB
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Process all XHTML files
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(('.xhtml', '.html')):
                    file_path = os.path.join(root, file)
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    fixed_content, fixes = fix_charset_quotes(content)
                    
                    if fixes > 0:
                        print(f"Applied {fixes} fixes to {file}")
                        total_fixes += fixes
                        
                        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
                            f.write(fixed_content)
        
        # Repack EPUB
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, temp_dir)
                    zip_out.write(file_path, arc_name)
    
    return total_fixes

def run_epubcheck(epub_path, output_file):
    """
    Run epubcheck validation
    """
    try:
        result = subprocess.run(
            ['java', '-jar', 'epubcheck.jar', epub_path],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n--- STDERR ---\n")
                f.write(result.stderr)
        
        print(f"Validation results saved to {output_file}")
        
        # Count errors
        output = result.stdout
        fatal_errors = output.count('FATAL')
        errors = output.count('ERROR') - fatal_errors  # Subtract fatal from total errors
        
        print(f"Validation complete: {fatal_errors} fatal errors, {errors} regular errors")
        
    except Exception as e:
        print(f"Error running epubcheck: {e}")

if __name__ == "__main__":
    input_epub = "doing2_manual_fixed.epub"
    output_epub = "doing2_ultimate_fixed.epub"
    validation_output = "ultimate_charset_validation.txt"
    
    if not os.path.exists(input_epub):
        print(f"Input file {input_epub} not found!")
        exit(1)
    
    print(f"Processing {input_epub}...")
    total_fixes = process_epub(input_epub, output_epub)
    
    print(f"\nTotal fixes applied: {total_fixes}")
    print(f"Output saved as: {output_epub}")
    
    # Run validation
    print("\nRunning epubcheck validation...")
    run_epubcheck(output_epub, validation_output)