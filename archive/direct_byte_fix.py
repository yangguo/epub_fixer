#!/usr/bin/env python3
import os
import zipfile
import tempfile
import subprocess

def fix_titlepage_meta(content):
    """
    Direct fix for the specific meta tag issue in titlepage.xhtml
    """
    lines = content.split('\n')
    
    # Fix line 4 (index 3) - the problematic meta tag
    if len(lines) > 3:
        line4 = lines[3]
        # Replace the problematic charset attribute
        if 'charset="UTF-8"' in line4:
            # Replace charset="UTF-8" with charset="UTF-8"
            fixed_line = line4.replace('charset="UTF-8"', 'charset="UTF-8"')
            lines[3] = fixed_line
            print(f"Fixed titlepage.xhtml line 4: {line4.strip()} -> {fixed_line.strip()}")
            return '\n'.join(lines), 1
    
    return content, 0

def process_epub(epub_path, output_path):
    """
    Process EPUB file to fix the specific titlepage issue
    """
    total_fixes = 0
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract EPUB
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Fix titlepage.xhtml specifically
        titlepage_path = os.path.join(temp_dir, 'titlepage.xhtml')
        if os.path.exists(titlepage_path):
            with open(titlepage_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            fixed_content, fixes = fix_titlepage_meta(content)
            
            if fixes > 0:
                total_fixes += fixes
                with open(titlepage_path, 'w', encoding='utf-8', newline='\n') as f:
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
        errors = output.count('ERROR') - fatal_errors
        
        print(f"Validation complete: {fatal_errors} fatal errors, {errors} regular errors")
        
    except Exception as e:
        print(f"Error running epubcheck: {e}")

if __name__ == "__main__":
    input_epub = "doing2_manual_fixed.epub"
    output_epub = "doing2_direct_fixed.epub"
    validation_output = "direct_validation.txt"
    
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