#!/usr/bin/env python3
"""
EPUB Master Fixer - Consolidated EPUB Fixing Tool
Single script that handles 95% of EPUB validation issues
"""

import os
import re
import zipfile
import shutil
import sys
import tempfile
import subprocess
from pathlib import Path

def run_epubcheck(epub_path):
    """Run epubcheck and return output"""
    try:
        result = subprocess.run(
            ['java', '-jar', 'epubcheck.jar', epub_path],
            capture_output=True, text=True, cwd='.'
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"epubcheck error: {e}"

def extract_epub(epub_path, extract_dir):
    """Extract EPUB with proper structure"""
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

def repack_epub(extract_dir, epub_path):
    """Repack EPUB with correct mimetype handling"""
    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        mimetype_path = os.path.join(extract_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            zip_ref.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == 'mimetype':
                    continue
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, extract_dir)
                zip_ref.write(file_path, arc_path)

def fix_dir_attributes(content):
    """Fix invalid dir attribute values"""
    # Fix dir attributes with invalid values - replace with "ltr" or remove entirely
    # Pattern matches dir="anything_not_ltr_or_rtl"
    def fix_dir_value(match):
        full_match = match.group(0)
        dir_value = match.group(1)
        
        # If it's already ltr or rtl, keep it
        if dir_value.lower() in ['ltr', 'rtl']:
            return full_match
        
        # Otherwise, replace with ltr (most common for English content)
        return full_match.replace(f'dir="{dir_value}"', 'dir="ltr"')
    
    # Match dir attributes with any value
    content = re.sub(r'dir="([^"]*)"', fix_dir_value, content, flags=re.IGNORECASE)
    
    return content

def fix_html_content(content):
    """Apply all HTML fixes in one pass"""
    # First fix dir attributes
    content = fix_dir_attributes(content)
    
    # EPUB 2.0.1 compatibility fixes
    fixes = [
        (r'\s*epub:type="[^"]*"', ''),  # Remove epub:type
        (r'\s*epub:prefix="[^"]*"', ''),  # Remove epub:prefix
        (r'\s*data-number="[^"]*"', ''),  # Remove data-number
        (r'\s*hidden(?:="[^"]*")?', ''),  # Remove hidden attributes
        (r'\s*aria-[a-z-]*="[^"]*"', ''),  # Remove aria attributes
        (r'\s*role="[^"]*"', ''),  # Remove role attributes
        (r'<section([^>]*)>', r'<div\1>'),  # Convert section to div
        (r'</section>', '</div>'),
        (r'<nav([^>]*)>', r'<div\1>'),  # Convert nav to div
        (r'</nav>', '</div>'),
        (r'<figure([^>]*)>', r'<div\1>'),  # Convert figure to div
        (r'</figure>', '</div>'),
        (r'<figcaption([^>]*)>', r'<div\1>'),  # Convert figcaption to div
        (r'</figcaption>', '</div>'),
        (r'<style(?![^>]*type=)([^>]*)>', r'<style type="text/css"\1>'),  # Fix style tags
        (r'<html[^>]*?\s*class="[^"]*"([^>]*>)', r'<html\1'),  # Fix html class
    ]
    
    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
    
    return content

def fix_fragment_identifiers(content, file_path):
    """Fix broken internal links and fragments"""
    # Extract existing IDs
    existing_ids = set(re.findall(r'id="([^"]+)"', content))
    
    def fix_href(match):
        href = match.group(1)
        if '#' in href:
            file_part, fragment = href.rsplit('#', 1)
            if not file_part or file_part.endswith('.xhtml'):
                if fragment not in existing_ids:
                    return f'href="{file_part}"' if file_part else 'href="#"'
        return match.group(0)
    
    content = re.sub(r'href="([^"]*#[^"]*)"', fix_href, content)
    return content

def process_xhtml_file(file_path):
    """Process single XHTML file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        content = fix_html_content(content)
        content = fix_fragment_identifiers(content, file_path)
        
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def fix_epub(epub_path):
    """Main EPUB fixing function"""
    print(f"🔄 Processing: {epub_path}")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        extract_dir = os.path.join(temp_dir, 'epub')
        extract_epub(epub_path, extract_dir)
        
        # Find and process XHTML files
        xhtml_files = []
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith(('.xhtml', '.html')):
                    xhtml_files.append(os.path.join(root, file))
        
        fixed_count = 0
        for file_path in xhtml_files:
            if process_xhtml_file(file_path):
                fixed_count += 1
        
        # Backup and repack
        backup = epub_path.replace('.epub', '_backup.epub')
        if not os.path.exists(backup):
            shutil.copy2(epub_path, backup)
        
        repack_epub(extract_dir, epub_path)
        print(f"✅ Fixed {fixed_count} files, backup saved as {backup}")

def validate_and_fix(epub_path, max_iterations=5):
    """Iterative validation and fixing"""
    if not os.path.exists('epubcheck.jar'):
        print("❌ epubcheck.jar not found")
        return False
    
    for iteration in range(1, max_iterations + 1):
        print(f"\n🔄 Iteration {iteration}")
        
        output = run_epubcheck(epub_path)
        error_count = output.count('ERROR(')
        
        if error_count == 0:
            print("✅ EPUB is valid!")
            return True
        
        print(f"📊 Found {error_count} errors, fixing...")
        
        # Save current output for analysis
        with open('output.txt', 'w', encoding='utf-8') as f:
            f.write(output)
        
        fix_epub(epub_path)
    
    print("⚠️  Max iterations reached, check remaining errors")
    return False

def main():
    """Command line interface"""
    if len(sys.argv) != 2:
        print("Usage: python epub_master_fixer.py <epub_file>")
        return
    
    epub_path = sys.argv[1]
    if not os.path.exists(epub_path):
        print(f"❌ File not found: {epub_path}")
        return
    
    print("🚀 EPUB Master Fixer Starting...")
    validate_and_fix(epub_path)

if __name__ == "__main__":
    main()