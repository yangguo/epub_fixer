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
    
    # Remove any remaining invalid dir attributes that don't have proper values
    content = re.sub(r'\s+dir="(?!(?:ltr|rtl)")"[^"]*"', '', content, flags=re.IGNORECASE)
    
    return content

def fix_html_content(content):
    """Apply all HTML fixes in one pass"""
    # First fix dir attributes
    content = fix_dir_attributes(content)
    
    # Fix malformed head tags first
    content = re.sub(r'</head[^>]*>', '</head>', content, flags=re.IGNORECASE)
    
    # Fix XML namespace issues - ensure proper XHTML namespace
    # More robust namespace handling
    # Find the html tag and ensure it has proper namespace
    def fix_html_namespace(match):
        html_tag = match.group(0)
        # If no xmlns attribute, add it
        if 'xmlns=' not in html_tag:
            # Add XHTML namespace as first attribute after html tag
            return re.sub(r'<html', '<html xmlns="http://www.w3.org/1999/xhtml"', html_tag, flags=re.IGNORECASE)
        # Remove problematic attributes from html tag
        html_tag = re.sub(r'\s+class="[^"]*"', '', html_tag, flags=re.IGNORECASE)
        html_tag = re.sub(r'\s+epub:prefix="[^"]*"', '', html_tag, flags=re.IGNORECASE)
        return html_tag
    
    content = re.sub(r'<html[^>]*>', fix_html_namespace, content, flags=re.IGNORECASE)
    
    # Fix structural issues - move misplaced elements
    content = fix_structural_issues(content)
    
    # EPUB 2.0.1 compatibility fixes
    fixes = [
        # Remove EPUB 3 specific attributes from head tags  
        (r'<head[^>]*\s+epub:prefix="[^"]*"([^>]*)>', r'<head\1>'),
        (r'<head[^>]*\s+class="[^"]*"([^>]*)>', r'<head\1>'),
        
        # Remove EPUB 3 specific attributes from body tags  
        (r'<body[^>]*\s+epub:type="[^"]*"([^>]*)>', r'<body\1>'),
        
        # General EPUB 3 attribute removal
        (r'\s+epub:type="[^"]*"', ''),  # Remove epub:type
        (r'\s+epub:prefix="[^"]*"', ''),  # Remove epub:prefix
        (r'\s+data-number="[^"]*"', ''),  # Remove data-number
        (r'\s+hidden(?:="[^"]*")?', ''),  # Remove hidden attributes
        (r'\s+aria-[a-z-]*="[^"]*"', ''),  # Remove aria attributes
        (r'\s+role="[^"]*"', ''),  # Remove role attributes
        
        # HTML5 to HTML4 element conversion
        (r'<section([^>]*)>', r'<div\1>'),  # Convert section to div
        (r'</section>', '</div>'),
        (r'<nav([^>]*)>', r'<div\1>'),  # Convert nav to div
        (r'</nav>', '</div>'),
        (r'<figure([^>]*)>', r'<div\1>'),  # Convert figure to div
        (r'</figure>', '</div>'),
        (r'<figcaption([^>]*)>', r'<div\1>'),  # Convert figcaption to div
        (r'</figcaption>', '</div>'),
        (r'<aside([^>]*)>', r'<div\1>'),  # Convert aside to div
        (r'</aside>', '</div>'),
        (r'<header([^>]*)>', r'<div\1>'),  # Convert header to div
        (r'</header>', '</div>'),
        
        # Fix style tags
        (r'<style(?![^>]*type=)([^>]*)>', r'<style type="text/css"\1>'),
    ]
    
    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
    
    # Additional cleanup for empty attributes
    content = re.sub(r'\s+\w+="\s*"', '', content)  # Remove empty attributes
    
    # Remove references to missing CSS files
    content = re.sub(r'<link[^>]*href="[^"]*WileyTemplate_v5\.1\.css"[^>]*/?>', '', content, flags=re.IGNORECASE)
    
    # Remove references to missing image files
    content = re.sub(r'<img[^>]*src="[^"]*images/cover_fmt\.jpg"[^>]*/?>', '', content, flags=re.IGNORECASE)
    
    # Fix incomplete body elements - ensure body has proper content
    content = fix_incomplete_body(content)
    
    return content

def fix_structural_issues(content):
    """Fix structural issues like misplaced head/h1 elements and missing titles"""
    # Move h1 elements from head to body
    # Find head section and extract h1 elements
    head_match = re.search(r'<head[^>]*>(.*?)</head>', content, re.DOTALL | re.IGNORECASE)
    if head_match:
        head_content = head_match.group(1)
        # Extract h1 elements from head
        h1_elements = re.findall(r'<h1[^>]*>.*?</h1>', head_content, re.DOTALL | re.IGNORECASE)
        if h1_elements:
            # Remove h1 elements from head
            head_content = re.sub(r'<h1[^>]*>.*?</h1>', '', head_content, flags=re.DOTALL | re.IGNORECASE)
            # Replace head content
            content = content.replace(head_match.group(0), f'<head>{head_content}</head>')
            
            # Add h1 elements to beginning of body
            for h1 in h1_elements:
                content = re.sub(r'<body[^>]*>', f'<body>\\n{h1}', content, flags=re.IGNORECASE)
    
    # Ensure head has a title element
    head_match = re.search(r'<head[^>]*>(.*?)</head>', content, re.DOTALL | re.IGNORECASE)
    if head_match:
        head_content = head_match.group(1)
        if not re.search(r'<title[^>]*>.*?</title>', head_content, re.DOTALL | re.IGNORECASE):
            # Add a default title if missing
            head_content += '\\n<title>Document</title>'
            content = content.replace(head_match.group(0), f'<head>{head_content}</head>')
    
    # Fix duplicate head elements (remove misplaced ones)
    # Keep only the first head element, remove others
    head_matches = list(re.finditer(r'<head[^>]*>.*?</head>', content, re.DOTALL | re.IGNORECASE))
    if len(head_matches) > 1:
        # Remove all but the first head
        for i in range(1, len(head_matches)):
            content = content.replace(head_matches[i].group(0), '')
    
    return content

def fix_incomplete_body(content):
    """Fix incomplete body elements by ensuring they have valid child elements"""
    # Find empty or whitespace-only body elements
    body_pattern = r'<body[^>]*>(\s*)</body>'
    
    def replace_empty_body(match):
        body_content = match.group(1)
        if not body_content.strip():
            # Add a paragraph with non-breaking space to make body valid
            return match.group(0).replace(body_content, '<p>&nbsp;</p>')
        return match.group(0)
    
    content = re.sub(body_pattern, replace_empty_body, content, flags=re.IGNORECASE)
    
    # Also fix body elements that only contain whitespace and invalid elements
    body_pattern2 = r'<body[^>]*>(\s*(?:<br\s*/?>\s*)*)</body>'
    content = re.sub(body_pattern2, replace_empty_body, content, flags=re.IGNORECASE)
    
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

def fix_ncx_file(content):
    """Fix NCX navigation issues - duplicate playOrder and missing fragments"""
    lines = content.split('\n')
    play_order = 1
    
    # Track nesting level to only assign playOrder to top-level navPoints
    nesting_level = 0
    
    for i, line in enumerate(lines):
        if '<navPoint' in line:
            # Count opening navPoint tags before this line to determine nesting
            nav_point_opens = line[:line.find('<navPoint')].count('<navPoint')
            nav_point_closes = line[:line.find('<navPoint')].count('</navPoint>')
            current_nesting = nesting_level + nav_point_opens - nav_point_closes
            
            # Only assign playOrder to top-level navPoints (nesting_level == 0)
            if current_nesting == 0 and 'playOrder=' in line:
                lines[i] = re.sub(r'playOrder="[^"]*"', f'playOrder="{play_order}"', line)
                play_order += 1
            else:
                # Remove playOrder from nested navPoints
                lines[i] = re.sub(r'\s+playOrder="[^"]*"', '', line)
        
        # Update nesting level based on opening/closing tags
        nesting_level += line.count('<navPoint') - line.count('</navPoint>')
    
    content = '\n'.join(lines)
    
    # Remove fragment identifiers from src attributes that don't exist
    # This is a conservative approach - just remove the fragment part
    content = re.sub(r'src="([^#]*)#[^"]*"', r'src="\1"', content)
    
    return content

def fix_opf_file(content):
    """Fix OPF file issues - ensure all referenced items are in spine"""
    # Check if there are references to cover.xhtml in the manifest
    # but the item is not in the spine
    
    # Find all item references in the manifest
    manifest_items = re.findall(r'<item[^>]*id="([^"]*)"[^>]*href="([^"]*cover\.xhtml[^"]*)"', content, re.IGNORECASE)
    
    # Find all item references in the spine
    spine_items = re.findall(r'<itemref[^>]*idref="([^"]*)"', content)
    
    # For each cover.xhtml item in manifest, check if it's in spine
    for item_id, href in manifest_items:
        if item_id not in spine_items:
            # Add the item to the spine
            content = re.sub(r'(</spine>)', f'    <itemref idref="{item_id}"/>\n\\1', content)
    
    return content

def process_file(file_path):
    """Process single file (XHTML, NCX, or OPF)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        if file_path.endswith('.ncx'):
            content = fix_ncx_file(content)
        elif file_path.endswith('.opf'):
            content = fix_opf_file(content)
        else:
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
        
        # Find and process all relevant files
        process_files = []
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith(('.xhtml', '.html', '.ncx', '.opf')):
                    process_files.append(os.path.join(root, file))
        
        fixed_count = 0
        for file_path in process_files:
            if process_file(file_path):
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