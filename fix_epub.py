#!/usr/bin/env python3
"""
EPUB Fixer Script
This script fixes common EPUB validation errors found by epubcheck.
Specifically handles EPUB 3.3 validation issues.
"""

import os
import re
import zipfile
import shutil
from pathlib import Path
import tempfile
import subprocess
import sys

def fix_role_attributes(content):
    """Fix invalid role attribute values according to EPUB 3.3 rules"""
    print("Fixing role attributes...")
    
    # For EPUB 2 compatibility, remove all role and aria-label attributes
    # as they are not allowed in EPUB 2 XHTML
    content = re.sub(r'\s*role="[^"]*"', '', content)
    content = re.sub(r'\s*aria-label="[^"]*"', '', content)
    content = re.sub(r'\s*aria-[^=]*="[^"]*"', '', content)
    
    return content

def fix_section_elements(content):
    """Replace section elements with div elements for EPUB 2 compatibility"""
    print("Fixing section elements...")
    
    # Replace opening section tags with div tags, preserving attributes
    content = re.sub(r'<section([^>]*)>', r'<div\1>', content)
    
    # Replace closing section tags
    content = re.sub(r'</section>', '</div>', content)
    
    return content

def fix_incomplete_body_elements(content):
    """Fix incomplete body elements by ensuring proper content structure"""
    print("Fixing incomplete body elements...")
    
    # If body element is immediately followed by closing body tag, add a paragraph
    content = re.sub(
        r'(<body[^>]*>)\s*(</body>)',
        r'\1\n<p></p>\n\2',
        content
    )
    
    # If body only contains section elements (now converted to div), ensure proper structure
    # This pattern matches body with only div elements that were sections
    content = re.sub(
        r'(<body[^>]*>)\s*(<div[^>]*>.*?</div>)\s*(</body>)',
        r'\1\n\2\n\3',
        content,
        flags=re.DOTALL
    )
    
    return content

def fix_h1_placement(content):
    """Fix H1 elements that are not allowed in their current context"""
    print("Fixing H1 element placement...")
    
    # Remove hgroup wrapper and convert to div with proper heading structure
    # This addresses the core issue where hgroup is causing validation problems
    content = re.sub(
        r'<hgroup>\s*<h1([^>]*)>(.*?)</h1>\s*<h1([^>]*)>(.*?)</h1>\s*</hgroup>',
        r'<div class="chapter-header"><h1\1>\2</h1><p\3>\4</p></div>',
        content,
        flags=re.DOTALL
    )
    
    # Handle single H1 in hgroup
    content = re.sub(
        r'<hgroup>\s*<h1([^>]*)>(.*?)</h1>\s*</hgroup>',
        r'<div class="chapter-header"><h1\1>\2</h1></div>',
        content,
        flags=re.DOTALL
    )
    
    # Fix any remaining H2 elements that were converted but still in problematic contexts
    content = re.sub(
        r'<hgroup>\s*<h2([^>]*)>(.*?)</h2>\s*<h2([^>]*)>(.*?)</h2>\s*</hgroup>',
        r'<div class="chapter-header"><h1\1>\2</h1><p\3>\4</p></div>',
        content,
        flags=re.DOTALL
    )
    
    content = re.sub(
        r'<hgroup>\s*<h2([^>]*)>(.*?)</h2>\s*</hgroup>',
        r'<div class="chapter-header"><h1\1>\2</h1></div>',
        content,
        flags=re.DOTALL
    )
    
    return content

def fix_deprecated_roles(content):
    """Fix deprecated doc-endnote roles"""
    print("Fixing deprecated doc-endnote roles...")
    
    # Replace deprecated doc-endnote with standard endnote or remove entirely
    content = re.sub(
        r'\s*role="doc-endnote"',
        '',
        content
    )
    
    # Alternative: replace with valid role if needed
    # content = re.sub(
    #     r'role="doc-endnote"',
    #     'role="note"',
    #     content
    # )
    
    return content

def fix_malformed_xml(content):
    """Fix specific malformed XML syntax errors"""
    print("Fixing malformed XML syntax...")
    
    # Fix the specific malformed charset pattern: charset="UTF-8"/> -> charset="UTF-8" />
    content = re.sub(r'charset="([^"]+)"/>', r'charset="\1" />', content)
    
    # Fix malformed meta tags with multiple forward slashes
    content = re.sub(r'(<meta[^>]*)/+\s*/>+', r'\1 />', content)
    
    # Fix malformed meta tags that end with "/> instead of " />
    content = re.sub(r'([^\s])"/>', r'\1" />', content)
    
    # Fix meta tags with malformed syntax like: <meta ... / />
    content = re.sub(r'<meta([^>]*?)\s+/\s+/>', r'<meta\1 />', content)
    
    # Fix malformed div tags missing closing bracket
    content = re.sub(r'<div([^>]*[^>])(<p>)', r'<div\1>\n\2', content)
    
    # Fix malformed paragraph tags missing closing bracket
    content = re.sub(r'</p(<p>)', r'</p>\n\1', content)
    
    # Fix missing quotes around attribute values
    content = re.sub(r'charset=([^\s>]+)(?=\s|>)', r'charset="\1"', content)
    
    # Fix double quotes issues
    content = re.sub(r'""', '"', content)
    
    # Fix meta tags that are not properly self-closed
    content = re.sub(r'<meta([^>]*)>(?!</meta>)', r'<meta\1 />', content)
    
    # Additional comprehensive fixes from specific scripts
    content = fix_charset_issues(content)
    content = fix_line_breaks_in_meta(content)
    content = fix_malformed_brackets(content)
    content = fix_meta_spacing_issues(content)
    content = fix_div_and_paragraph_elements(content)
    
    return content

def fix_charset_issues(content):
    """Fix various charset-related issues in meta tags"""
    # Fix charset with line breaks: charset="utf-8" \r\n/>
    content = re.sub(r'charset="utf-8"\s*\r\n/>', 'charset="utf-8" />', content)
    content = re.sub(r'charset="UTF-8"\s*\r\n/>', 'charset="UTF-8" />', content)
    
    # Fix charset with newlines: charset="utf-8" \n/>
    content = re.sub(r'charset="utf-8"\s*\n/>', 'charset="utf-8" />', content)
    content = re.sub(r'charset="UTF-8"\s*\n/>', 'charset="UTF-8" />', content)
    
    # Fix charset with extra quotes: charset="utf-8" /"
    content = re.sub(r'charset="utf-8"\s*/"', 'charset="utf-8" />', content)
    content = re.sub(r'charset="UTF-8"\s*/"', 'charset="UTF-8" />', content)
    
    # Fix charset missing closing bracket: charset="utf-8"/
    content = re.sub(r'charset="utf-8"/', 'charset="utf-8"/>', content)
    content = re.sub(r'charset="UTF-8"/', 'charset="UTF-8"/>', content)
    
    # Fix charset with extra closing bracket: charset="utf-8"/>">
    content = re.sub(r'charset="utf-8"/>">', 'charset="utf-8"/>', content)
    content = re.sub(r'charset="UTF-8"/>">', 'charset="UTF-8"/>', content)
    
    return content

def fix_line_breaks_in_meta(content):
    """Fix line breaks in meta tags"""
    # Fix meta tags with line breaks before />
    content = re.sub(r'charset="utf-8"\s*\n\s*/>', 'charset="utf-8" />', content)
    content = re.sub(r'charset="UTF-8"\s*\n\s*/>', 'charset="UTF-8" />', content)
    
    # Fix specific pattern: charset="utf-8" \n/>
    content = content.replace('charset="utf-8" \n/>', 'charset="utf-8" />')
    content = content.replace('charset="UTF-8" \n/>', 'charset="UTF-8" />')
    
    return content

def fix_malformed_brackets(content):
    """Fix malformed brackets in meta tags"""
    # Fix pattern: charset="utf-8" / -> charset="utf-8"/>
    content = re.sub(r'charset="utf-8"\s*/>', 'charset="utf-8"/>', content)
    content = re.sub(r'charset="UTF-8"\s*/>', 'charset="UTF-8"/>', content)
    
    return content

def fix_meta_spacing_issues(content):
    """Fix spacing issues in meta tags"""
    def fix_meta_closure(match):
        tag = match.group(0)
        # If it ends with /> but doesn't have a space before it, add one
        if tag.endswith('/>'):
            if not tag.endswith(' />'):
                tag = tag[:-2] + ' />'
        return tag
    
    # Fix all meta tags spacing
    content = re.sub(r'<meta[^>]*/?>', fix_meta_closure, content)
    
    return content

def fix_div_and_paragraph_elements(content):
    """Fix malformed div and paragraph elements"""
    # Fix div elements missing closing >
    content = re.sub(r'<div([^>]*?)(<[^>]*?>)', r'<div\1>\2', content)
    
    # Fix paragraph tags that are missing closing >
    content = re.sub(r'<p([^>]*?)(<[^>]*?>)', r'<p\1>\2', content)
    
    # Fix specific pattern in cover.xhtml where div id="cover-alt" is missing >
    content = re.sub(r'<div id="cover-alt"<p>', '<div id="cover-alt"><p>', content)
    
    # Fix paragraph tags that are missing closing >
    content = re.sub(r'<p>([^<]*?)<p>', r'<p>\1</p><p>', content)
    
    # Fix paragraph tags that end with content but no closing tag before next element
    content = re.sub(r'<p>([^<]*?)<([^/][^>]*?)>', r'<p>\1</p><\2>', content)
    
    # Fix specific pattern where paragraph content ends without proper closing
    content = re.sub(r'<p>([^<]+?)(<[^/])', r'<p>\1</p>\2', content)
    
    return content

def fix_css_references(content):
    """Remove or fix CSS references that don't exist"""
    # Remove references to missing CSS files
    content = re.sub(r'<link[^>]*href="[^"]*9781501154577\.css"[^>]*>', '', content)
    content = re.sub(r'<link[^>]*href="[^"]*SS_global\.css"[^>]*>', '', content)
    
    return content

def fix_fragment_identifiers(content):
    """Fix or remove problematic fragment identifier links"""
    # Remove href attributes that point to non-existent fragments
    # Keep the link text but remove the problematic href
    content = re.sub(r'<a href="[^"]*#[^"]*"([^>]*)>([^<]*)</a>', r'\2', content)
    
    # Fix self-referencing links that might be problematic
    content = re.sub(r'href="#[^"]*"', 'href="#"', content)
    
    return content

def clean_meta_encoding(content):
    """Clean meta tags by removing problematic characters and ensuring proper formatting"""
    # Remove any null bytes or other control characters
    content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
    
    # Fix meta tags - ensure they are properly self-closed
    def fix_meta_tag(match):
        tag = match.group(0)
        # Remove any trailing spaces before the closing
        tag = re.sub(r'\s+/>', '/>', tag)
        tag = re.sub(r'\s+>', '>', tag)
        
        # Ensure self-closing tags end with />
        if '<meta' in tag and not tag.endswith('/>'):
            if tag.endswith('>'):
                tag = tag[:-1] + ' />'
            else:
                tag += ' />'
        
        return tag
    
    # Fix all meta tags
    content = re.sub(r'<meta[^>]*/?>', fix_meta_tag, content)
    
    return content

def fix_opf_metadata(content):
    """Fix OPF metadata structure and namespace issues"""
    print("Fixing OPF metadata structure...")
    
    # Fix malformed metadata element that is self-closing but has content after it
    # Pattern: <metadata ... /> followed by content that should be inside metadata
    content = re.sub(
        r'(<metadata[^>]*)/>(\s*<dc:)',
        r'\1>\2',
        content
    )
    
    # Ensure metadata element is properly closed
    if '<metadata' in content and '</metadata>' not in content:
        # Find the last meta element and add closing metadata tag after it
        content = re.sub(
            r'(\s*<meta[^>]*/>\s*)(</metadata>)?\s*(</package>)',
            r'\1\n</metadata>\n\3',
            content
        )
    
    # Fix missing namespace declarations in package element
    if 'xmlns:dc=' not in content:
        content = re.sub(
            r'(<package[^>]*)(>)',
            r'\1 xmlns:dc="http://purl.org/dc/elements/1.1/"\2',
            content
        )
    
    return content

def fix_fragment_identifiers(content, file_path):
    """Fix fragment identifier errors by removing or fixing broken links"""
    print(f"Fixing fragment identifiers in {file_path}...")
    
    # Extract all id attributes in the document to build a valid id list
    id_pattern = r'id="([^"]+)"'
    valid_ids = set(re.findall(id_pattern, content))
    
    # Find all href fragments
    href_pattern = r'href="([^"]*#[^"]+)"'
    
    def fix_href(match):
        href = match.group(1)
        if '#' in href:
            file_part, fragment = href.split('#', 1)
            
            # If it's a local fragment (same file) and the id doesn't exist
            if not file_part and fragment not in valid_ids:
                # Remove the fragment part, just keep the file reference
                return f'href="{file_part}"' if file_part else 'href="#"'
            
            # If it's an external file reference, we can't easily validate
            # so we'll leave it as is for now
        
        return match.group(0)
    
    content = re.sub(href_pattern, fix_href, content)
    
    return content



def fix_epub2_compatibility(content):
    """Fix EPUB 2 compatibility issues by removing EPUB 3 features"""
    print("Applying EPUB 2 compatibility fixes...")
    
    # Fix malformed XML first
    content = fix_malformed_xml(content)
    
    # Remove epub:prefix attribute from html element
    content = re.sub(r'\s*epub:prefix="[^"]*"', '', content)
    
    # Remove epub:type attributes
    content = re.sub(r'\s*epub:type="[^"]*"', '', content)
    
    # Remove role attributes and any associated aria attributes
    content = re.sub(r'\s*role="[^"]*"', '', content)
    content = re.sub(r'\s*aria-[^=]+="[^"]*"', '', content)
    
    # Remove hidden attribute (HTML5 attribute not allowed in EPUB 2)
    content = re.sub(r'\s*hidden(?:="[^"]*")?', '', content)
    
    # Remove class attribute from html element (not allowed in EPUB 2)
    content = re.sub(r'(<html[^>]*)\s*class="[^"]*"', r'\1', content)
    
    # Replace HTML5 semantic elements with div (not allowed in EPUB 2)
    html5_elements = ['section', 'nav', 'article', 'aside', 'header', 'footer', 'main', 'figure', 'figcaption']
    for element in html5_elements:
        # Preserve any existing attributes when converting to div
        content = re.sub(f'<{element}([^>]*?)>', r'<div\1>', content)
        content = re.sub(f'</{element}>', r'</div>', content)
    
    # Remove xmlns:epub namespace declaration
    content = re.sub(r'\s*xmlns:epub="[^"]*"', '', content)
    
    # Update DOCTYPE to XHTML 1.1
    content = re.sub(
        r'<!DOCTYPE html[^>]*>',
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">',
        content
    )
    
    # Fix text content directly in body elements - wrap in paragraphs
    content = fix_direct_text_in_body(content)
    
    # Fix text content directly in blockquote elements - wrap in paragraphs
    content = fix_direct_text_in_blockquote(content)
    
    # Fix incomplete body elements by ensuring they have block-level content
    content = fix_incomplete_body_elements(content)
    
    return content

def fix_ncx_identifier_mismatch(ncx_path, opf_path):
    """Fix NCX identifier mismatch with OPF file"""
    print("Fixing NCX identifier mismatch...")
    
    try:
        # Read OPF to get unique identifier
        with open(opf_path, 'r', encoding='utf-8') as f:
            opf_content = f.read()
        
        # Extract unique identifier from OPF
        opf_id_match = re.search(r'<dc:identifier[^>]*id="([^"]+)"[^>]*>([^<]+)</dc:identifier>', opf_content)
        if not opf_id_match:
            print("Could not find unique identifier in OPF")
            return False
        
        opf_identifier = opf_id_match.group(2).strip()
        
        # Read and update NCX
        with open(ncx_path, 'r', encoding='utf-8') as f:
            ncx_content = f.read()
        
        # Update NCX identifier
        ncx_content = re.sub(
            r'(<meta name="dtb:uid" content=")[^"]*("/>)',
            f'\\1{opf_identifier}\\2',
            ncx_content
        )
        
        # Write back NCX
        with open(ncx_path, 'w', encoding='utf-8') as f:
            f.write(ncx_content)
        
        print(f"Updated NCX identifier to: {opf_identifier}")
        return True
        
    except Exception as e:
        print(f"Error fixing NCX identifier: {str(e)}")
        return False

def fix_ncx_playorder(ncx_path):
    """Fix NCX play order sequence"""
    print("Fixing NCX play order...")
    
    try:
        with open(ncx_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all navPoint elements and fix playOrder
        play_order = 1
        
        def replace_playorder(match):
            nonlocal play_order
            result = re.sub(r'playOrder="\d+"', f'playOrder="{play_order}"', match.group(0))
            play_order += 1
            return result
        
        content = re.sub(r'<navPoint[^>]*>', replace_playorder, content)
        
        with open(ncx_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Fixed NCX play order for {play_order - 1} navigation points")
        return True
        
    except Exception as e:
        print(f"Error fixing NCX play order: {str(e)}")
        return False

def fix_direct_text_in_body(content):
    """Fix text content directly in body elements by wrapping in paragraphs"""
    print("Fixing direct text content in body elements...")
    
    def wrap_loose_text(match):
        body_attrs = match.group(1) if match.group(1) else ''
        body_content = match.group(2)
        
        # If body is essentially empty (just whitespace), add a paragraph with non-breaking space
        if not body_content.strip():
            return f'<body{body_attrs}>\n    <p>&#160;</p>\n</body>'
        
        # Remove problematic nested paragraph structures and malformed content
        body_content = re.sub(r'<p>\s*>\s*</p>', '', body_content)
        body_content = re.sub(r'>\s*<p>', '<p>', body_content)
        body_content = re.sub(r'</p>\s*>', '</p>', body_content)
        
        # Remove standalone '>' characters that are not part of tags
        lines = body_content.split('\n')
        fixed_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Skip lines that are just '>' or empty
            if stripped == '>' or not stripped:
                if not stripped:  # Keep empty lines for formatting
                    fixed_lines.append(line)
                continue
            
            # Clean up lines that start with '>' but have content
            if stripped.startswith('>'):
                clean_line = re.sub(r'^>+\s*', '', stripped)
                if clean_line:
                    # If it's not already in a tag, wrap it
                    if not clean_line.startswith('<') and not re.search(r'<(?:address|blockquote|del|div|dl|h[1-6]|hr|ins|noscript|ol|p|pre|script|table|ul)', line):
                        fixed_lines.append(f'    <p>{clean_line}</p>')
                    else:
                        fixed_lines.append(line.replace('>' + stripped[1:], clean_line))
                continue
            
            fixed_lines.append(line)
        
        return f'<body{body_attrs}>\n' + '\n'.join(fixed_lines) + '\n</body>'
    
    # Apply the fix
    content = re.sub(r'<body([^>]*)>(.*?)</body>', wrap_loose_text, content, flags=re.DOTALL)
    
    return content

def fix_direct_text_in_blockquote(content):
    """Fix text content directly in blockquote elements by wrapping in paragraphs"""
    print("Fixing direct text content in blockquote elements...")
    
    # First, fix malformed blockquote tags
    content = re.sub(r'<blockquote([^>]*[^>])<p', r'<blockquote\1><p', content)
    content = re.sub(r'<blockquote([^>]*[^>])([^<])', r'<blockquote\1>\2', content)
    
    # Fix nested paragraph structures in blockquotes
    def fix_nested_paragraphs(match):
        blockquote_attrs = match.group(1)
        blockquote_content = match.group(2)
        
        # Remove nested paragraph structures
        while '<p<p' in blockquote_content or '<p><p>' in blockquote_content:
            blockquote_content = re.sub(r'<p<p', '<p', blockquote_content)
            blockquote_content = re.sub(r'<p><p>', '<p>', blockquote_content)
            blockquote_content = re.sub(r'</p></p>', '</p>', blockquote_content)
        
        # Extract the actual text content
        text_match = re.search(r'<p[^>]*>([^<]+)</p>', blockquote_content)
        if text_match:
            clean_text = text_match.group(1).strip()
            if clean_text and clean_text != 'class="epigraph" dir="ltr" lang="en"':
                return f'<blockquote{blockquote_attrs}><p>{clean_text}</p></blockquote>'
        
        return f'<blockquote{blockquote_attrs}><p>&#160;</p></blockquote>'
    
    content = re.sub(r'<blockquote([^>]*)>(.*?)</blockquote>', fix_nested_paragraphs, content, flags=re.DOTALL)
    
    return content

def fix_malformed_tags(content):
    """Fix malformed HTML tags that are missing closing brackets"""
    print("Fixing malformed HTML tags...")
    
    # Remove extra '>' characters that may have been added
    content = re.sub(r'/>>{2,}', '/>', content)
    content = re.sub(r'">{2,}', '">', content)
    
    # Fix specific malformed blockquote pattern: <blockquote class="epigraph" dir="ltr" lang="en"<p>
    content = re.sub(r'<blockquote([^>]+)"<p>', r'<blockquote\1"><p>', content)
    
    # Fix specific malformed li pattern: <li class="indexmain" id="idx1_X"<p>
    content = re.sub(r'<li([^>]+)"<p>', r'<li\1"><p>', content)
    
    # Fix specific malformed li pattern: <li class="calibre8"<a>
    content = re.sub(r'<li([^>]+)"<a>', r'<li\1"><a>', content)
    
    return content



def fix_incomplete_body_elements(content):
    """Fix incomplete body elements by ensuring they have proper block-level content"""
    print("Fixing incomplete body elements...")
    
    # Find body elements that are empty or only contain whitespace/inline elements
    def fix_empty_body(match):
        body_content = match.group(1).strip()
        if not body_content:
            # Empty body - add a paragraph
            return f'<body{match.group(0)[5:match.group(0).find(">")+1]}>\n    <p>&#160;</p>\n</body>'
        
        # Check if body only contains inline elements or text
        if not re.search(r'<(?:address|blockquote|del|div|dl|h[1-6]|hr|ins|noscript|ol|p|pre|script|table|ul)', body_content):
            # Only inline content - wrap in paragraph
            return f'<body{match.group(0)[5:match.group(0).find(">")+1]}>\n    <p>{body_content}</p>\n</body>'
        
        return match.group(0)
    
    content = re.sub(r'<body[^>]*>(.*?)</body>', fix_empty_body, content, flags=re.DOTALL)
    
    return content

def fix_xhtml_file(file_path, content, epub_version='epub3'):
    """Apply all XHTML fixes to a file based on EPUB version"""
    print(f"Fixing XHTML file: {file_path} (target: {epub_version})")
    
    if epub_version.lower() == 'epub2':
        # Apply EPUB 2 compatibility fixes
        content = fix_epub2_compatibility(content)
    else:
        # Apply EPUB 3 fixes
        content = fix_role_attributes(content)
        content = fix_h1_placement(content)
        content = fix_deprecated_roles(content)
    
    # Apply common fixes for both EPUB 2 and 3
    content = fix_section_elements(content)
    content = fix_incomplete_body_elements(content)
    
    # Fix malformed HTML tags
    content = fix_malformed_tags(content)
    
    return content

def extract_epub(epub_path, extract_dir):
    """Extract EPUB file to directory"""
    print(f"Extracting EPUB: {epub_path} to {extract_dir}")
    
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    return True

def repack_epub(extract_dir, output_path):
    """Repack directory into EPUB file"""
    print(f"Repacking EPUB from {extract_dir} to {output_path}")
    
    # Remove existing output file if it exists
    if os.path.exists(output_path):
        os.remove(output_path)
    
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
                arc_path = os.path.relpath(file_path, extract_dir)
                zip_ref.write(file_path, arc_path)
    
    return True

def run_epubcheck(epub_path, output_file=None):
    """Run epubcheck on EPUB file and return results"""
    print(f"Running epubcheck on: {epub_path}")
    
    jar_path = os.path.join(os.path.dirname(__file__), 'epubcheck.jar')
    
    if not os.path.exists(jar_path):
        print(f"Error: epubcheck.jar not found at {jar_path}")
        return False, "epubcheck.jar not found"
    
    try:
        cmd = ['java', '-jar', jar_path, epub_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        output = result.stdout + result.stderr
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
        
        # Check if there are any errors (not just warnings)
        has_errors = 'ERROR(' in output
        
        return not has_errors, output
        
    except subprocess.TimeoutExpired:
        return False, "epubcheck timed out"
    except Exception as e:
        return False, f"Error running epubcheck: {str(e)}"

def fix_empty_titles(content):
    """Fix empty title elements in XHTML files"""
    print("Fixing empty title elements...")
    
    # Replace empty title tags with a default title
    content = re.sub(
        r'<title></title>',
        '<title>Chapter</title>',
        content
    )
    
    # Also handle title tags with only whitespace
    content = re.sub(
        r'<title>\s*</title>',
        '<title>Chapter</title>',
        content
    )
    
    return content

def fix_invalid_width_attributes(content):
    """Fix invalid width attribute values"""
    print("Fixing invalid width attributes...")
    
    # Replace percentage width values with valid integer or remove
    content = re.sub(
        r'width="100%"',
        'style="width: 100%"',
        content
    )
    
    # Fix other percentage values
    content = re.sub(
        r'width="(\d+)%"',
        r'style="width: \1%"',
        content
    )
    
    return content

def fix_opf_metadata(opf_path):
    """Fix OPF metadata issues"""
    print("Fixing OPF metadata issues...")
    
    try:
        with open(opf_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Remove invalid opf:role and opf:file-as attributes from dc:creator
        content = re.sub(
            r'(<dc:creator[^>]*?)\s+opf:role="[^"]*"',
            r'\1',
            content
        )
        
        content = re.sub(
            r'(<dc:creator[^>]*?)\s+opf:file-as="[^"]*"',
            r'\1',
            content
        )
        
        # Remove invalid opf:scheme attributes from dc:identifier and dc:date
        content = re.sub(
            r'(<dc:identifier[^>]*?)\s+opf:scheme="[^"]*"',
            r'\1',
            content
        )
        
        content = re.sub(
            r'(<dc:date[^>]*?)\s+opf:scheme="[^"]*"',
            r'\1',
            content
        )
        
        # Add required dcterms:modified meta element if missing
        if 'dcterms:modified' not in content:
            # Find the end of metadata section
            metadata_end = content.find('</metadata>')
            if metadata_end != -1:
                from datetime import datetime
                current_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
                modified_meta = f'    <meta property="dcterms:modified">{current_time}</meta>\n'
                content = content[:metadata_end] + modified_meta + content[metadata_end:]
        
        # Fix empty guide element by removing it or adding a reference
        content = re.sub(
            r'\s*<guide/>',
            '',
            content
        )
        
        content = re.sub(
            r'\s*<guide>\s*</guide>',
            '',
            content
        )
        
        # Fix existing nav item linear attribute if present
        content = re.sub(
            r'<itemref idref="nav" linear="no"/>',
            '<itemref idref="nav"/>',
            content
        )
        
        # Add navigation manifest item if missing
        if 'properties="nav"' not in content:
            # Find a suitable place to add nav item (after other manifest items)
            manifest_items = re.findall(r'<item [^>]*href="Text/[^"]*\.xhtml"[^>]*>', content)
            if manifest_items:
                # Add nav item after the first text item
                first_item = manifest_items[0]
                nav_item = '\n    <item href="Text/nav.xhtml" id="nav" media-type="application/xhtml+xml" properties="nav"/>'
                content = content.replace(first_item, first_item + nav_item)
                
                # Also add to spine if not present
                if 'idref="nav"' not in content:
                    spine_start = content.find('<spine')
                    if spine_start != -1:
                        spine_end = content.find('>', spine_start) + 1
                        nav_itemref = '\n    <itemref idref="nav"/>'
                        content = content[:spine_end] + nav_itemref + content[spine_end:]
        
        if content != original_content:
            with open(opf_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error fixing OPF metadata: {str(e)}")
        return False

def create_nav_file(extract_dir):
    """Create a basic navigation file if missing"""
    print("Creating navigation file...")
    
    nav_path = None
    text_dir = None
    
    # Find the Text directory
    for root, dirs, files in os.walk(extract_dir):
        if 'Text' in dirs:
            text_dir = os.path.join(root, 'Text')
            nav_path = os.path.join(text_dir, 'nav.xhtml')
            break
    
    if not nav_path or os.path.exists(nav_path):
        return False
    
    try:
        # Create a basic navigation file
        nav_content = '''<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh-TW">
<head>
  <title>Navigation</title>
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>Table of Contents</h1>
    <ol>
      <li><a href="A01_Cover.xhtml">Cover</a></li>
    </ol>
  </nav>
</body>
</html>'''
        
        with open(nav_path, 'w', encoding='utf-8') as f:
            f.write(nav_content)
        
        print(f"Created navigation file: {nav_path}")
        return True
        
    except Exception as e:
        print(f"Error creating navigation file: {str(e)}")
        return False

def fix_opf_file(file_path, content, epub_version='epub3'):
    """Fix OPF file issues for EPUB 2 compatibility"""
    print(f"Fixing OPF file: {file_path} (target: {epub_version})")
    
    # Fix malformed metadata element - remove self-closing when it has child elements
    content = re.sub(r'<metadata([^>]*?)\s*/>', r'<metadata\1>', content)
    content = re.sub(r'<metadata([^>]*?)\s*/\s*/\s*/\s*/\s*/>', r'<metadata\1>', content)
    
    # Fix malformed meta tags with extra slashes and spaces
    content = re.sub(r'<meta([^>]*?)\s*/\s*/\s*/\s*/\s*/\s*/>', r'<meta\1 />', content)
    content = re.sub(r'<meta([^>]*?)\s*/\s*/>', r'<meta\1 />', content)
    content = re.sub(r'<meta([^>]*?)\s*/\s*/>', r'<meta\1 />', content)
    
    # Fix malformed meta tags with property attributes and extra slashes
    content = re.sub(r'<meta\s+property="([^"]+)"\s*>([^<]+)</meta>\s*/\s*/>', r'<meta name="\1" content="\2" />', content)
    
    # Apply general fixes
    content = fix_malformed_xml(content)
    
    # Fix malformed meta tags with property attribute that should be name/content
    # Convert <meta property="dcterms:modified">value</meta> to proper format
    content = re.sub(
        r'<meta property="dcterms:modified">([^<]+)</meta>',
        r'<meta name="dcterms:modified" content="\1"/>',
        content
    )
    
    # Fix malformed meta tags with extra slashes and spaces
    content = re.sub(r'<meta([^>]*?)\s*/\s*/\s*/\s*/\s*/\s*/>', r'<meta\1 />', content)
    content = re.sub(r'<meta([^>]*?)\s*/\s*/>', r'<meta\1 />', content)
    
    # Fix malformed meta tags with property attributes and extra slashes
    content = re.sub(r'<meta\s+property="([^"]+)"\s*>([^<]+)</meta>\s*/\s*/>', r'<meta name="\1" content="\2" />', content)
    
    if epub_version.lower() == 'epub2':
        # Remove EPUB 3 meta elements with property attribute
        content = re.sub(r'\s*<meta\s+property="[^"]*"[^>]*>.*?</meta>', '', content, flags=re.DOTALL)
        content = re.sub(r'\s*<meta\s+property="[^"]*"[^>]*/>', '', content)
        
        # Fix meta elements that have property but no name/content
        content = re.sub(r'<meta\s+property="[^"]*"([^>]*)>', r'<!-- Removed EPUB 3 meta element -->', content)
        
        # Remove xmlns:epub namespace from package element
        content = re.sub(r'\s*xmlns:epub="[^"]*"', '', content)
        
        # Update package version to 2.0
        content = re.sub(r'version="3\.[0-9]+"', 'version="2.0"', content)
    
    return content

def fix_epub_files(extract_dir, epub_version='epub3'):
    """Fix all XHTML files in the extracted EPUB"""
    print(f"Fixing EPUB files for {epub_version.upper()} compatibility...")
    
    fixed_files = []
    
    # Find and fix OPF files first
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith('.opf'):
                opf_path = os.path.join(root, file)
                if fix_opf_metadata(opf_path):
                    fixed_files.append(opf_path)
                    print(f"Fixed OPF: {opf_path}")
    
    # Create navigation file if needed
    if create_nav_file(extract_dir):
        nav_path = os.path.join(extract_dir, 'OEBPS', 'Text', 'nav.xhtml')
        if os.path.exists(nav_path):
            fixed_files.append(nav_path)
    
    # Find all XHTML files
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith(('.xhtml', '.html')):
                file_path = os.path.join(root, file)
                
                # Skip nav.xhtml for EPUB 2 conversion (not compatible)
                if epub_version.lower() == 'epub2' and file == 'nav.xhtml':
                    continue
                
                try:
                    # Read file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Apply fixes
                    original_content = content
                    content = fix_xhtml_file(file_path, content, epub_version)
                    content = fix_empty_titles(content)
                    content = fix_invalid_width_attributes(content)
                    content = fix_fragment_identifiers(content, file_path)
                    
                    # Write back if changed
                    if content != original_content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        fixed_files.append(file_path)
                        print(f"Fixed: {file_path}")
                
                except Exception as e:
                    print(f"Error fixing {file_path}: {str(e)}")
            
            elif file.endswith('.opf'):
                file_path = os.path.join(root, file)
                try:
                    # Read file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Apply OPF fixes
                    original_content = content
                    content = fix_opf_file(file_path, content, epub_version)
                    
                    # Write back if changed
                    if content != original_content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        fixed_files.append(file_path)
                        print(f"Fixed OPF: {file_path}")
                
                except Exception as e:
                    print(f"Error fixing OPF {file_path}: {str(e)}")
    
    # Fix NCX files if present (common in both EPUB 2 and 3)
    ncx_files = []
    opf_files = []
    
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith('.ncx'):
                ncx_files.append(os.path.join(root, file))
            elif file.endswith('.opf'):
                opf_files.append(os.path.join(root, file))
    
    # Fix NCX issues
    for ncx_path in ncx_files:
        try:
            # Fix NCX play order
            if fix_ncx_playorder(ncx_path):
                fixed_files.append(ncx_path)
            
            # Fix NCX identifier mismatch if OPF is available
            if opf_files:
                if fix_ncx_identifier_mismatch(ncx_path, opf_files[0]):
                    if ncx_path not in fixed_files:
                        fixed_files.append(ncx_path)
        
        except Exception as e:
            print(f"Error fixing NCX {ncx_path}: {str(e)}")
    
    return fixed_files

def main(epub_version='epub3', epub_file='japan1.epub'):
    """Main function to fix EPUB iteratively"""
    output_file = 'output.txt'
    max_iterations = 5
    
    if not os.path.exists(epub_file):
        print(f"Error: {epub_file} not found")
        return False
    
    print(f"Starting iterative EPUB fixing for: {epub_file} (target: {epub_version.upper()})")
    
    for iteration in range(1, max_iterations + 1):
        print(f"\n=== Iteration {iteration} ===")
        
        # Create temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            extract_dir = os.path.join(temp_dir, 'epub_extracted')
            
            # Extract EPUB
            if not extract_epub(epub_file, extract_dir):
                print("Failed to extract EPUB")
                return False
            
            # Fix files
            fixed_files = fix_epub_files(extract_dir, epub_version)
            
            if fixed_files:
                print(f"Fixed {len(fixed_files)} files in this iteration")
                
                # Create backup of original
                backup_file = f"{epub_file}.backup.{iteration}"
                if not os.path.exists(backup_file):
                    shutil.copy2(epub_file, backup_file)
                    print(f"Created backup: {backup_file}")
                
                # Repack EPUB
                if not repack_epub(extract_dir, epub_file):
                    print("Failed to repack EPUB")
                    return False
            else:
                print("No files needed fixing in this iteration")
            
            # Run epubcheck
            success, output = run_epubcheck(epub_file, output_file)
            
            print(f"\nEpubcheck results for iteration {iteration}:")
            
            # Count errors and warnings
            error_count = output.count('ERROR(')
            warning_count = output.count('WARNING(')
            
            print(f"Errors: {error_count}, Warnings: {warning_count}")
            
            if success:
                print(f"\n🎉 SUCCESS! EPUB is now valid after {iteration} iteration(s)")
                print(f"Final validation results saved to: {output_file}")
                return True
            
            if error_count == 0:
                print(f"\n✅ No more errors! Only {warning_count} warnings remain.")
                print(f"EPUB is valid after {iteration} iteration(s)")
                print(f"Final validation results saved to: {output_file}")
                return True
            
            if not fixed_files:
                print(f"\n⚠️  No files were fixed in this iteration, but errors remain.")
                print("This might indicate errors that require manual intervention.")
                break
    
    print(f"\n❌ Could not fix all errors after {max_iterations} iterations")
    print(f"Final validation results saved to: {output_file}")
    print("Manual intervention may be required for remaining errors.")
    return False

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix EPUB validation errors for EPUB 2 or EPUB 3')
    parser.add_argument('--version', choices=['epub2', 'epub3'], default='epub3',
                       help='Target EPUB version (default: epub3)')
    parser.add_argument('--file', default='japan1.epub',
                       help='EPUB file to fix (default: japan1.epub)')
    
    args = parser.parse_args()
    
    # Call main function with both version and file parameters
    success = main(args.version, args.file)
    
    if success:
        print(f"\n✅ EPUB successfully fixed for {args.version.upper()} compatibility!")
    else:
        print(f"\n❌ Failed to fix all EPUB errors. Manual intervention may be required.")
        sys.exit(1)
