#!/usr/bin/env python3

import zipfile
import os
import re
import subprocess
import tempfile
import shutil

def extract_epub(epub_path, extract_dir):
    """Extract EPUB to directory"""
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir)
    
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print(f"Extracted EPUB to {extract_dir}")

def fix_meta_charset(content):
    """Fix the specific charset issue in meta tags"""
    fixes_applied = 0
    
    # Pattern to match: charset=""UTF-8" (with extra quote)
    pattern = r'charset=""UTF-8"'
    replacement = 'charset="UTF-8"'
    
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
        fixes_applied += 1
        print(f"Fixed charset pattern: {pattern} -> {replacement}")
    
    # Also check for lowercase utf-8
    pattern_lower = r'charset=""utf-8"'
    replacement_lower = 'charset="utf-8"'
    
    if re.search(pattern_lower, content):
        content = re.sub(pattern_lower, replacement_lower, content)
        fixes_applied += 1
        print(f"Fixed charset pattern: {pattern_lower} -> {replacement_lower}")
    
    return content, fixes_applied

def process_xhtml_files(extract_dir):
    """Process all XHTML files to fix meta tag issues"""
    total_fixes = 0
    
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith('.xhtml') or file.endswith('.html'):
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    original_content = content
                    content, fixes = fix_meta_charset(content)
                    
                    if fixes > 0:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        print(f"Applied {fixes} fixes to {file_path}")
                        total_fixes += fixes
                        
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
    
    return total_fixes

def create_epub(extract_dir, output_path):
    """Create EPUB from extracted directory"""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        # Add mimetype first (uncompressed)
        mimetype_path = os.path.join(extract_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            zip_ref.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == 'mimetype':
                    continue  # Already added
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, extract_dir)
                zip_ref.write(file_path, arcname)
    
    print(f"Created EPUB: {output_path}")

def run_epubcheck(epub_path, output_file):
    """Run epubcheck validation"""
    try:
        result = subprocess.run(
            ['java', '-jar', 'epubcheck.jar', epub_path],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        # Write validation output to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n--- STDERR ---\n")
                f.write(result.stderr)
        
        print(f"Validation results written to {output_file}")
        
        # Parse results
        if "0 fatal / 0 errors" in result.stdout:
            print("✅ EPUB is valid!")
            return True
        else:
            # Extract error counts
            import re
            match = re.search(r'(\d+) fatal / (\d+) errors', result.stdout)
            if match:
                fatal, errors = match.groups()
                print(f"❌ Validation failed: {fatal} fatal errors, {errors} regular errors")
            return False
            
    except Exception as e:
        print(f"Error running epubcheck: {e}")
        return False

def main():
    epub_path = "doing2_direct_fixed.epub"
    extract_dir = "final_meta_debug"
    output_epub = "doing2_final_fixed.epub"
    validation_file = "final_meta_validation.txt"
    
    print("=== Final Meta Tag Fix ===")
    
    # Extract EPUB
    extract_epub(epub_path, extract_dir)
    
    # Fix meta tags
    total_fixes = process_xhtml_files(extract_dir)
    print(f"\nTotal fixes applied: {total_fixes}")
    
    # Create new EPUB
    create_epub(extract_dir, output_epub)
    
    # Validate
    print("\n=== Running EPUBCheck ===")
    is_valid = run_epubcheck(output_epub, validation_file)
    
    if is_valid:
        print("\n🎉 SUCCESS! EPUB is now valid!")
    else:
        print("\n❌ EPUB still has validation errors. Check the validation file for details.")

if __name__ == "__main__":
    main()