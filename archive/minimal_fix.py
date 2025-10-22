#!/usr/bin/env python3
import zipfile
import os
import shutil
import subprocess
import re

def extract_epub(epub_path, extract_dir):
    """Extract EPUB to directory"""
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir)
    
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print(f"Extracted EPUB to {extract_dir}")

def fix_meta_tags_minimal(file_path):
    """Fix meta tags with minimal changes, preserving original formatting"""
    print(f"Checking {file_path}...")
    
    # Read file as bytes to preserve exact formatting
    with open(file_path, 'rb') as f:
        content_bytes = f.read()
    
    original_content = content_bytes
    fixes_applied = 0
    
    # Look for the specific problematic pattern: charset=""UTF-8"
    # This pattern has an extra quote before UTF-8
    patterns_to_fix = [
        (rb'charset=""UTF-8"', rb'charset="UTF-8"'),
        (rb'charset=""utf-8"', rb'charset="utf-8"'),
    ]
    
    for old_pattern, new_pattern in patterns_to_fix:
        if old_pattern in content_bytes:
            print(f"Found pattern {old_pattern} in {file_path}")
            content_bytes = content_bytes.replace(old_pattern, new_pattern)
            fixes_applied += 1
            print(f"Fixed pattern in {file_path}")
    
    # Only write if changes were made
    if content_bytes != original_content:
        with open(file_path, 'wb') as f:
            f.write(content_bytes)
        print(f"Applied {fixes_applied} fixes to {file_path}")
    else:
        print(f"No fixes needed for {file_path}")
    
    return fixes_applied

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
    extract_dir = "minimal_debug"
    output_epub = "doing2_minimal_fixed.epub"
    validation_file = "minimal_validation.txt"
    
    print("=== Minimal EPUB Fix ===")
    
    # Extract EPUB
    extract_epub(epub_file, extract_dir)
    
    # Fix all XHTML files
    total_fixes = 0
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith('.xhtml'):
                file_path = os.path.join(root, file)
                fixes = fix_meta_tags_minimal(file_path)
                total_fixes += fixes
    
    print(f"\nTotal fixes applied: {total_fixes}")
    
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