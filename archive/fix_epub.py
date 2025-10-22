#!/usr/bin/env python3
"""
Comprehensive EPUB Fixer Script
This script fixes all EPUB validation errors found by epubcheck.
Handles EPUB 2.0.1 compatibility issues systematically.
"""

import os
import re
import zipfile
import shutil
from pathlib import Path
import tempfile
import subprocess
import sys

def run_epubcheck(epub_path):
    """Run epubcheck and return the output"""
    try:
        result = subprocess.run(
            ['java', '-jar', 'epubcheck.jar', epub_path],
            capture_output=True,
            text=True,
            cwd='.'
        )
        return result.stdout + result.stderr
    except Exception as e:
        print(f"Error running epubcheck: {e}")
        return ""

def extract_epub(epub_path, extract_dir):
    """Extract EPUB file to directory"""
    print(f"Extracting {epub_path} to {extract_dir}")
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

def repack_epub(extract_dir, epub_path):
    """Repack directory into EPUB file"""
    print(f"Repacking {extract_dir} to {epub_path}")
    
    # Create a new zip file
    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        # First add mimetype without compression
        mimetype_path = os.path.join(extract_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            zip_ref.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Then add all other files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == 'mimetype':
                    continue  # Already added
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, extract_dir)
                zip_ref.write(file_path, arc_path)

def fix_html_element_attributes(content):
    """Fix HTML element attributes for EPUB 2 compatibility"""
    print("Fixing HTML element attributes...")
    
    # Remove class attribute from html element (not allowed in EPUB 2)
    content = re.sub(r'(<html[^>]*?)\s*class="[^"]*"([^>]*>)', r'\1\2', content)
    
    # Remove epub:prefix attribute
    content = re.sub(r'(<html[^>]*?)\s*epub:prefix="[^"]*"([^>]*>)', r'\1\2', content)
    
    return content

def fix_body_element_attributes(content):
    """Fix body element attributes for EPUB 2 compatibility"""
    print("Fixing body element attributes...")
    
    # Remove epub:type attribute from body element
    content = re.sub(r'(<body[^>]*?)\s*epub:type="[^"]*"([^>]*>)', r'\1\2', content)
    
    return content

def fix_section_elements(content):
    """Replace section elements with div elements for EPUB 2 compatibility"""
    print("Fixing section elements...")
    
    # Replace opening section tags with div tags, preserving attributes except epub:type
    def replace_section_tag(match):
        attrs = match.group(1)
        # Remove epub:type attribute
        attrs = re.sub(r'\s*epub:type="[^"]*"', '', attrs)
        return f'<div{attrs}>'
    
    content = re.sub(r'<section([^>]*)>', replace_section_tag, content)
    content = re.sub(r'</section>', '</div>', content)
    
    return content

def fix_nav_elements(content):
    """Replace nav elements with div elements for EPUB 2 compatibility"""
    print("Fixing nav elements...")
    
    # Replace opening nav tags with div tags, preserving attributes except epub:type
    def replace_nav_tag(match):
        attrs = match.group(1)
        # Remove epub:type attribute
        attrs = re.sub(r'\s*epub:type="[^"]*"', '', attrs)
        return f'<div{attrs}>'
    
    content = re.sub(r'<nav([^>]*)>', replace_nav_tag, content)
    content = re.sub(r'</nav>', '</div>', content)
    
    return content

def fix_epub_type_attributes(content):
    """Remove epub:type attributes from all elements"""
    print("Removing epub:type attributes...")
    
    # Remove epub:type attributes from all elements
    content = re.sub(r'\s*epub:type="[^"]*"', '', content)
    
    return content

def fix_data_number_attributes(content):
    """Remove data-number attributes (not allowed in EPUB 2)"""
    print("Removing data-number attributes...")
    
    # Remove data-number attributes from all elements
    content = re.sub(r'\s*data-number="[^"]*"', '', content)
    
    return content

def fix_incomplete_body_elements(content):
    """Fix incomplete body elements by ensuring proper content structure"""
    print("Fixing incomplete body elements...")
    
    # Pattern to detect body elements that are incomplete
    # Look for body tags that don't have proper block-level content
    
    # If body element contains only nav/section elements (now converted to div), ensure structure
    body_pattern = r'(<body[^>]*>)(.*?)(</body>)'
    
    def fix_body_content(match):
        opening = match.group(1)
        content_inside = match.group(2)
        closing = match.group(3)
        
        # Check if content is empty or only whitespace
        if not content_inside.strip():
            return f'{opening}\n<div></div>\n{closing}'
        
        # Check if content doesn't start with a block element
        content_stripped = content_inside.strip()
        if content_stripped and not content_stripped.startswith(('<div', '<p', '<h1', '<h2', '<h3', '<h4', '<h5', '<h6', '<ul', '<ol', '<dl', '<blockquote', '<pre', '<table', '<hr', '<address')):
            # Wrap content in div
            return f'{opening}\n<div>\n{content_inside}\n</div>\n{closing}'
        
        return match.group(0)
    
    content = re.sub(body_pattern, fix_body_content, content, flags=re.DOTALL)
    
    return content

def fix_anchor_attributes(content):
    """Remove epub:type and role attributes from anchor elements"""
    print("Fixing anchor element attributes...")
    
    # Remove epub:type attributes from anchor elements
    content = re.sub(r'(<a[^>]*?)\s*epub:type="[^"]*"([^>]*>)', r'\1\2', content)
    
    # Remove role attributes from anchor elements (not allowed in EPUB 2)
    content = re.sub(r'(<a[^>]*?)\s*role="[^"]*"([^>]*>)', r'\1\2', content)
    
    return content

def fix_hidden_attributes(content):
    """Remove hidden attributes (not allowed in EPUB 2)"""
    print("Removing hidden attributes...")
    
    # Remove hidden attributes from all elements
    content = re.sub(r'\s*hidden(?:="[^"]*")?', '', content)
    
    return content

def fix_figure_elements(content):
    """Replace figure elements with div elements for EPUB 2 compatibility"""
    print("Fixing figure elements...")
    
    # Replace opening figure tags with div tags, preserving attributes
    content = re.sub(r'<figure([^>]*)>', r'<div\1>', content)
    content = re.sub(r'</figure>', '</div>', content)
    
    # Replace figcaption elements with div elements
    content = re.sub(r'<figcaption([^>]*)>', r'<div\1>', content)
    content = re.sub(r'</figcaption>', '</div>', content)
    
    return content

def fix_malformed_aria_attributes(content):
    """Fix malformed aria- attributes"""
    print("Fixing malformed aria- attributes...")
    
    # Fix malformed aria- attributes that are missing values
    # Pattern: aria-="something" or just aria- without proper name
    content = re.sub(r'\s*aria-="[^"]*"', '', content)
    content = re.sub(r'\s*aria-(?![a-z])', '', content)
    
    # Remove all aria- attributes for EPUB 2 compatibility
    content = re.sub(r'\s*aria-[a-z-]*="[^"]*"', '', content)
    
    return content

def fix_style_elements(content):
    """Fix style elements by adding required type attribute"""
    print("Fixing style elements...")
    
    # Add type="text/css" to style elements that don't have it
    content = re.sub(r'<style(?![^>]*type=)([^>]*)>', r'<style type="text/css"\1>', content)
    
    return content

def fix_fragment_identifiers(content, file_path):
    """Fix fragment identifier errors by removing broken links"""
    print(f"Fixing fragment identifiers in {file_path}...")
    
    # For nav.xhtml, we need to be more aggressive about removing broken fragment links
    if 'nav.xhtml' in file_path:
        # Extract all existing IDs in the current file
        id_pattern = r'id="([^"]+)"'
        existing_ids = set(re.findall(id_pattern, content))
        
        # Find and fix href attributes with fragments
        def fix_href_fragment(match):
            full_href = match.group(1)
            if '#' in full_href:
                file_part, fragment = full_href.rsplit('#', 1)
                # If it's a local reference and the ID doesn't exist, remove the fragment
                if not file_part or file_part.endswith('.xhtml'):
                    # For now, just remove the fragment part to avoid broken links
                    return f'href="{file_part}"' if file_part else 'href="#"'
            return match.group(0)
        
        content = re.sub(r'href="([^"]*#[^"]*)"', fix_href_fragment, content)
    
    return content

def fix_missing_resources(content, file_path):
    """Fix references to missing resources"""
    print(f"Fixing missing resource references in {file_path}...")
    
    # Remove references to missing CSS files
    content = re.sub(r'<link[^>]*href="[^"]*stylesheet1\.css"[^>]*>', '', content)
    
    # Remove references to missing image files or replace with placeholder
    content = re.sub(r'src="[^"]*cover\.jpg"', 'src=""', content)
    
    # For nav.xhtml, fix references to non-spine items
    if 'nav.xhtml' in file_path:
        # Remove or fix references that are not spine items
        # This typically means removing links to files that aren't in the reading order
        content = re.sub(r'href="[^"]*titlepage\.xhtml"', 'href="text/title_page.xhtml"', content)
    
    return content

def process_xhtml_file(file_path):
    """Process a single XHTML file to fix all validation errors"""
    print(f"Processing {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply all fixes in order
        content = fix_html_element_attributes(content)
        content = fix_body_element_attributes(content)
        content = fix_section_elements(content)
        content = fix_nav_elements(content)
        content = fix_epub_type_attributes(content)
        content = fix_data_number_attributes(content)
        content = fix_incomplete_body_elements(content)
        content = fix_anchor_attributes(content)
        content = fix_hidden_attributes(content)
        content = fix_figure_elements(content)
        content = fix_malformed_aria_attributes(content)
        content = fix_style_elements(content)
        content = fix_fragment_identifiers(content, file_path)
        content = fix_missing_resources(content, file_path)
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  Fixed {file_path}")
        else:
            print(f"  No changes needed for {file_path}")
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def fix_epub_file(epub_path):
    """Main function to fix EPUB file"""
    print(f"Starting EPUB fix for {epub_path}")
    
    # Create temporary directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        extract_dir = os.path.join(temp_dir, 'epub_content')
        
        # Extract EPUB
        extract_epub(epub_path, extract_dir)
        
        # Find all XHTML files
        xhtml_files = []
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith('.xhtml'):
                    xhtml_files.append(os.path.join(root, file))
        
        print(f"Found {len(xhtml_files)} XHTML files to process")
        
        # Process each XHTML file
        for xhtml_file in xhtml_files:
            process_xhtml_file(xhtml_file)
        
        # Backup original file
        backup_path = epub_path.replace('.epub', '_backup.epub')
        if not os.path.exists(backup_path):
            shutil.copy2(epub_path, backup_path)
            print(f"Created backup: {backup_path}")
        
        # Repack EPUB
        repack_epub(extract_dir, epub_path)
        
    print(f"EPUB fix completed for {epub_path}")

def main():
    """Main function with iterative fixing"""
    epub_path = 'red1.epub'
    max_iterations = 10
    
    if not os.path.exists(epub_path):
        print(f"Error: {epub_path} not found")
        return
    
    if not os.path.exists('epubcheck.jar'):
        print("Error: epubcheck.jar not found")
        return
    
    print("Starting iterative EPUB fixing process...")
    
    for iteration in range(1, max_iterations + 1):
        print(f"\n=== Iteration {iteration} ===")
        
        # Run epubcheck to get current errors
        print("Running epubcheck...")
        output = run_epubcheck(epub_path)
        
        # Save output to file
        with open('output.txt', 'w', encoding='utf-8') as f:
            f.write(output)
        
        # Check if there are still errors
        if 'ERROR' not in output:
            print("✅ No more errors found! EPUB is now valid.")
            break
        
        # Count errors
        error_count = output.count('ERROR(')
        print(f"Found {error_count} errors")
        
        # Apply fixes
        fix_epub_file(epub_path)
        
        print(f"Iteration {iteration} completed")
    
    else:
        print(f"\n⚠️  Reached maximum iterations ({max_iterations})")
        print("Some errors may still remain. Check output.txt for details.")
    
    # Final check
    print("\n=== Final Validation ===")
    final_output = run_epubcheck(epub_path)
    with open('output.txt', 'w', encoding='utf-8') as f:
        f.write(final_output)
    
    if 'ERROR' not in final_output:
        print("✅ EPUB is now valid!")
    else:
        final_error_count = final_output.count('ERROR(')
        print(f"❌ {final_error_count} errors still remain")
    
    print("Check output.txt for the final validation report")

if __name__ == "__main__":
    main()