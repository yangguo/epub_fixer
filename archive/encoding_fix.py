#!/usr/bin/env python3
import zipfile
import os
import shutil
import subprocess
import tempfile

def extract_epub(epub_path, extract_dir):
    """Extract EPUB to directory"""
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir)
    
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print(f"Extracted EPUB to {extract_dir}")

def fix_titlepage_encoding(titlepage_path):
    """Fix encoding issues in titlepage.xhtml"""
    print(f"Analyzing {titlepage_path}...")
    
    # Read the file as bytes first
    with open(titlepage_path, 'rb') as f:
        content_bytes = f.read()
    
    print(f"Original file size: {len(content_bytes)} bytes")
    
    # Try to decode as UTF-8 and re-encode cleanly
    try:
        content_str = content_bytes.decode('utf-8')
        print("Successfully decoded as UTF-8")
        
        # Look for the problematic line
        lines = content_str.split('\n')
        for i, line in enumerate(lines):
            if 'charset=' in line:
                print(f"Line {i+1}: {repr(line)}")
                
                # Clean up the charset line - ensure proper quotes
                if 'charset="UTF-8"' in line:
                    # The line looks correct, but let's rebuild it cleanly
                    new_line = '        <meta http-equiv="Content-Type" content="text/html; charset=\"UTF-8\" />'
                    if line.strip() != new_line.strip():
                        print(f"Replacing line {i+1}")
                        print(f"Old: {repr(line)}")
                        print(f"New: {repr(new_line)}")
                        lines[i] = new_line
                        
                        # Write back the corrected content
                        corrected_content = '\n'.join(lines)
                        with open(titlepage_path, 'w', encoding='utf-8') as f:
                            f.write(corrected_content)
                        print("Fixed titlepage.xhtml")
                        return 1
                    else:
                        print("Line appears correct, no changes needed")
                        return 0
        
        print("No charset line found to fix")
        return 0
        
    except UnicodeDecodeError as e:
        print(f"UTF-8 decode error: {e}")
        # Try other encodings
        for encoding in ['latin1', 'cp1252', 'iso-8859-1']:
            try:
                content_str = content_bytes.decode(encoding)
                print(f"Successfully decoded as {encoding}")
                # Re-encode as UTF-8
                with open(titlepage_path, 'w', encoding='utf-8') as f:
                    f.write(content_str)
                print(f"Re-encoded file as UTF-8")
                return 1
            except UnicodeDecodeError:
                continue
        
        print("Could not decode file with any common encoding")
        return 0

def repack_epub(extract_dir, output_epub):
    """Repack directory into EPUB"""
    with zipfile.ZipFile(output_epub, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add mimetype first (uncompressed)
        mimetype_path = os.path.join(extract_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            zipf.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == 'mimetype':
                    continue  # Already added
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, extract_dir)
                zipf.write(file_path, arc_path)
    
    print(f"Repacked EPUB as {output_epub}")

def validate_epub(epub_path):
    """Validate EPUB using epubcheck"""
    try:
        result = subprocess.run(
            ['java', '-jar', 'epubcheck.jar', epub_path],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", f"Error running epubcheck: {e}", 1

def main():
    epub_file = "doing2.epub"
    extract_dir = "encoding_debug"
    output_epub = "doing2_encoding_fixed.epub"
    validation_file = "encoding_validation.txt"
    
    print("=== EPUB Encoding Fix ===")
    
    # Extract EPUB
    extract_epub(epub_file, extract_dir)
    
    # Fix titlepage.xhtml
    titlepage_path = os.path.join(extract_dir, "titlepage.xhtml")
    if os.path.exists(titlepage_path):
        fixes_applied = fix_titlepage_encoding(titlepage_path)
        print(f"Applied {fixes_applied} fixes to titlepage.xhtml")
    else:
        print("titlepage.xhtml not found")
        return
    
    # Repack EPUB
    repack_epub(extract_dir, output_epub)
    
    # Validate
    print("\n=== Validating EPUB ===")
    stdout, stderr, returncode = validate_epub(output_epub)
    
    # Save validation results
    with open(validation_file, 'w') as f:
        f.write(stdout)
        if stderr:
            f.write("\n--- STDERR ---\n")
            f.write(stderr)
    
    print(f"Validation results saved to {validation_file}")
    
    # Parse results
    if "0 fatal" in stdout and "0 errors" in stdout:
        print("✅ EPUB is now valid!")
    else:
        # Extract error counts
        lines = stdout.split('\n')
        for line in lines:
            if 'fatal' in line and 'errors' in line:
                print(f"❌ Validation result: {line}")
                break

if __name__ == "__main__":
    main()