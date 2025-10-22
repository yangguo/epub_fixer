#!/usr/bin/env python3
"""
Fix line endings in EPUB files
"""

import os
import zipfile
import subprocess

def fix_line_endings(content):
    """
    Convert Windows line endings (CRLF) to Unix line endings (LF)
    """
    # Replace \r\n with \n
    fixed_content = content.replace('\r\n', '\n')
    # Also remove any standalone \r characters
    fixed_content = fixed_content.replace('\r', '\n')
    return fixed_content

def process_epub_line_endings(input_path, output_path):
    """
    Process EPUB and fix line endings in all text files
    """
    total_fixes = 0
    
    # Extract EPUB
    extract_dir = 'line_ending_fix_temp'
    if os.path.exists(extract_dir):
        import shutil
        shutil.rmtree(extract_dir)
    
    with zipfile.ZipFile(input_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # Process all text files (XHTML, XML, CSS, etc.)
    text_extensions = ['.xhtml', '.html', '.xml', '.css', '.ncx', '.opf']
    
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_ext = os.path.splitext(file)[1].lower()
            
            if file_ext in text_extensions:
                try:
                    # Read file in binary mode to preserve exact content
                    with open(file_path, 'rb') as f:
                        content_bytes = f.read()
                    
                    # Decode to string
                    content = content_bytes.decode('utf-8')
                    
                    # Check if file has CRLF line endings
                    if '\r\n' in content or '\r' in content:
                        print(f"Fixing line endings in {file}")
                        
                        # Fix line endings
                        fixed_content = fix_line_endings(content)
                        
                        # Write back with UTF-8 encoding and LF line endings
                        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
                            f.write(fixed_content)
                        
                        total_fixes += 1
                
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
    output_epub = 'doing2_line_endings_fixed.epub'
    validation_file = 'line_endings_validation.txt'
    
    if not os.path.exists(input_epub):
        print(f"Input file {input_epub} not found!")
        return
    
    print("Starting line endings fix...")
    
    # Process the EPUB
    fixes_applied = process_epub_line_endings(input_epub, output_epub)
    
    print(f"\nFixed line endings in {fixes_applied} files. Running validation...")
    
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