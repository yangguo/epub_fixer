#!/usr/bin/env python3
import os
import re
import zipfile
import shutil
import subprocess
import sys

def extract_epub(epub_path, extract_dir):
    """Extract EPUB file to directory"""
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir)
    
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print(f"Extracted EPUB to {extract_dir}")

def repack_epub(extract_dir, epub_path):
    """Repack directory to EPUB file"""
    if os.path.exists(epub_path):
        os.remove(epub_path)
    
    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, extract_dir)
                zip_ref.write(file_path, arc_name)
    print(f"Repacked EPUB to {epub_path}")

def fix_malformed_meta_tags(content):
    """Fix malformed meta tags with specific patterns"""
    # Fix meta tags with / /> ending
    content = re.sub(r'<meta([^>]*?)\s*/\s*/>', r'<meta\1 />', content)
    
    # Fix meta tags with missing closing
    content = re.sub(r'<meta([^>]*?)\s*(?<!/)>', r'<meta\1 />', content)
    
    # Fix charset meta tags specifically
    content = re.sub(r'<meta\s+http-equiv="Content-Type"\s+content="text/html;\s*charset="utf-8"\s*/\s*/>', 
                     '<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />', content)
    
    # Fix other malformed meta patterns
    content = re.sub(r'<meta\s+content="([^"]*?)"\s+name="([^"]*?)"\s*/\s*/>', 
                     r'<meta content="\1" name="\2" />', content)
    
    return content

def fix_malformed_img_tags(content):
    """Fix malformed img tags"""
    # Fix img tags with malformed alt and src
    content = re.sub(r'<img\s+alt="\s*src="([^"]*?)"([^>]*?)\s*/\s*/>', 
                     r'<img alt="" src="\1"\2 />', content)
    
    # Fix img tags with / /> ending
    content = re.sub(r'<img([^>]*?)\s*/\s*/>', r'<img\1 />', content)
    
    return content

def process_xhtml_file(file_path):
    """Process a single XHTML file to fix issues"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply fixes
        content = fix_malformed_meta_tags(content)
        content = fix_malformed_img_tags(content)
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def run_epubcheck(epub_path):
    """Run epubcheck on the EPUB file"""
    try:
        result = subprocess.run(
            ['java', '-jar', 'epubcheck.jar', epub_path],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        print("\n=== EPUBCHECK RESULTS ===")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("--- STDERR ---")
            print(result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error running epubcheck: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python fix_final_issues.py <epub_file>")
        sys.exit(1)
    
    epub_file = sys.argv[1]
    if not os.path.exists(epub_file):
        print(f"EPUB file not found: {epub_file}")
        sys.exit(1)
    
    extract_dir = "temp_fix_extract"
    
    try:
        # Extract EPUB
        extract_epub(epub_file, extract_dir)
        
        # Process all XHTML and HTML files
        files_fixed = 0
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith(('.xhtml', '.html')):
                    file_path = os.path.join(root, file)
                    if process_xhtml_file(file_path):
                        files_fixed += 1
        
        print(f"\nFixed {files_fixed} files")
        
        # Repack EPUB
        repack_epub(extract_dir, epub_file)
        
        # Run epubcheck
        print("\nRunning epubcheck...")
        success = run_epubcheck(epub_file)
        
        if success:
            print("\n✓ EPUB validation successful!")
        else:
            print("\n✗ EPUB validation failed. Check errors above.")
        
        # Cleanup
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()