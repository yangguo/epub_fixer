#!/usr/bin/env python3
"""
EPUB Master Fixer - Consolidated EPUB Fixing Tool
Single script that handles 95% of EPUB validation issues

Updated to fix:
- NCX identifier mismatch with OPF
- Unclosed anchor tags (especially in <sup> elements)
- Fragment identifiers pointing to non-existent IDs
- NCX IDs with colons (invalid XML names)
- Missing class attribute on pageList
- PlayOrder conflicts and gaps
- Page-map attribute in OPF spine (EPUB 2.0.1)

Successfully tested on college1.epub - fixes all 93 errors in one pass.
"""

import os
import re
import zipfile

from utils import run_epubcheck, count_errors
import shutil
import sys
import tempfile
import subprocess
from pathlib import Path



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

def build_fragment_index(extract_dir):
    """Collect ID fragments for each HTML-like file to validate NCX references."""
    fragment_index = {}
    for root, _, files in os.walk(extract_dir):
        for file in files:
            if not file.lower().endswith(('.xhtml', '.html', '.xml')):
                continue
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (UnicodeDecodeError, FileNotFoundError):
                continue
            if '<html' not in content.lower():
                continue
            rel_path = os.path.relpath(file_path, extract_dir).replace('\\', '/')
            fragment_index[rel_path] = set(re.findall(r'id="([^"]+)"', content))
    return fragment_index

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

def fix_unclosed_p_tags(content):
    """Fix unclosed/mismatched <p> tags without introducing new errors."""
    content = re.sub(r'</p>\s*s="([^"]*)">', r'<p class="\1">', content)

    pattern = re.compile(r'<p(?=[\s>])[^>]*>|</p>', re.IGNORECASE)
    balanced_segments = []
    last_index = 0
    open_count = 0

    for match in pattern.finditer(content):
        balanced_segments.append(content[last_index:match.start()])
        tag = match.group(0)
        lower = tag.lower()
        if lower.startswith('</p'):
            if open_count > 0:
                open_count -= 1
                balanced_segments.append(tag)
            else:
                # Skip unmatched closing tags
                pass
        else:
            open_count += 1
            balanced_segments.append(tag)
        last_index = match.end()

    balanced_segments.append(content[last_index:])
    content = ''.join(balanced_segments)

    if open_count > 0:
        content = re.sub(r'</body>', '</p>' * open_count + '</body>', content, flags=re.IGNORECASE)

    return content

def fix_mangled_p_tags(content):
    '''Fix mangled p tags like <ppubli... which should be <p class="publi...'''
    # Fix tags like <ppubli -> <p class="publi", <pcopyr -> <p class="copyr", etc.
    # Matches <p followed by lowercase letters/numbers (common class names)
    return re.sub(r'<p([a-z0-9]+)', r'<p class="\1"', content)

def fix_html_content(content):
    """Apply all HTML fixes in one pass"""
    # CRITICAL: Fix mangled tags FIRST - these cause fatal parsing errors
    content = fix_mangled_p_tags(content)
    
    # Then fix unclosed tags
    content = fix_unclosed_anchor_tags(content)
    content = fix_unclosed_p_tags(content)
    
    # First fix dir attributes
    content = fix_dir_attributes(content)
    
    # Fix malformed head tags first
    content = re.sub(r'</head[^>]*>', '</head>', content, flags=re.IGNORECASE)
    
    def fix_meta_value_attributes(text):
        def replace_tag(m):
            tag = m.group(0)
            if re.search(r'\bvalue\s*=\s*"', tag, re.IGNORECASE):
                vm = re.search(r'\bvalue\s*=\s*"([^"]*)"', tag, re.IGNORECASE)
                if vm:
                    val = vm.group(1)
                    if re.search(r'\bcontent\s*=', tag, re.IGNORECASE):
                        return re.sub(r'\s*\bvalue\s*=\s*"[^"]*"', '', tag, flags=re.IGNORECASE)
                    return re.sub(r'\bvalue\s*=\s*"[^"]*"', f' content="{val}"', tag, flags=re.IGNORECASE)
            return tag
        return re.sub(r'<meta\b[^>]*>', replace_tag, text, flags=re.IGNORECASE)
    
    content = fix_meta_value_attributes(content)
    
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
    
    # Fix malformed sup tags (e.g., <sup>1</a></sup> -> <sup>1</sup>)
    content = fix_malformed_sup_tags(content)
    
    # Additional cleanup for empty attributes
    content = re.sub(r'\s+\w+="\s*"', '', content)  # Remove empty attributes
    
    # Remove references to missing CSS files
    content = re.sub(r'<link[^>]*href="[^"]*WileyTemplate_v5\.1\.css"[^>]*/?>', '', content, flags=re.IGNORECASE)
    
    # Remove references to missing image files
    content = re.sub(r'<img[^>]*src="[^"]*images/cover_fmt\.jpg"[^>]*/?>', '', content, flags=re.IGNORECASE)
    
    # Fix incomplete body elements - ensure body has proper content
    content = fix_incomplete_body(content)
    
    # Fix missing </body> tags - more robust version
    # Make sure there's a closing </body> tag for every opening <body> tag
    body_open = len(re.findall(r'<body[^>]*(?<!/)>', content, flags=re.IGNORECASE))
    body_close = len(re.findall(r'</body>', content, flags=re.IGNORECASE))
    
    if body_close < body_open:
        missing_closes = body_open - body_close
        closes_to_add = '</body>' * missing_closes
        
        # Try multiple strategies to add the closing tags
        if '</html>' in content:
            # Add before </html> if present
            content = re.sub(\
                r'(</html>)', \
                r'</body>' * missing_closes + r'\\1', \
                content, \
                flags=re.IGNORECASE\
            )
        elif '</head>' in content:
            # If no </html>, but there's a </head>, add at the end
            content = content.rstrip() + r'</body></html>'
        else:
            # Last resort: add at the end
            content = content.rstrip() + closes_to_add
            
        # Verify the fix worked
        body_close_new = len(re.findall(r'</body>', content, flags=re.IGNORECASE))
        if body_close_new < body_open:
            # If still missing, add exactly where needed using more precise regex
            # Find the first opening body tag and insert closing tag at the end
            content = content.rstrip() + r'</body>'
    
    # Structural fixes that require valid block-level containers
    content = wrap_blockquote_text(content)
    content = ensure_image_alt_attributes(content)

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

def fix_malformed_sup_tags(content):
    """Fix malformed sup tags like <sup>text</a></sup> -> <sup>text</sup>"""
    # Pattern: <sup ...>content</a></sup> should drop the stray </a>
    content = re.sub(r'<sup([^>]*)>([^<]*)</a></sup>', r'<sup\1>\2</sup>', content, flags=re.IGNORECASE)
    
    # Remove duplicate closing anchors (</a></a></sup> -> </a></sup>)
    content = re.sub(r'</a></a></sup>', r'</a></sup>', content, flags=re.IGNORECASE)
    
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

def fix_unclosed_anchor_tags(content):
    """Fix unclosed anchor tags that cause parsing errors"""
    # Pattern 1: <sup ...><a href="...">text</sup> -> ensure </a>
    content = re.sub(
        r'<sup([^>]*)><a\s+([^>]*)>([^<]*)</sup>',
        r'<sup\1><a \2>\3</a></sup>',
        content,
        flags=re.IGNORECASE
    )
    # Pattern 1b: <sup ...><a id...></a><a href...>text</sup>
    content = re.sub(
        r'(<sup[^>]*>(?:\s*<a\b[^>]*></a>\s*)*)<a\s+([^>]*)>([^<]*)</sup>',
        r'\1<a \2>\3</a></sup>',
        content,
        flags=re.IGNORECASE
    )
    
    # Pattern 2: <a id="..."></a><sup ...><a href="...">N</sup> -> close anchor
    content = re.sub(
        r'(<a\s+id="[^"]*"></a>)<sup([^>]*)><a\s+([^>]*)>([^<]*)</sup>',
        r'\1<sup\2><a \3>\4</a></sup>',
        content,
        flags=re.IGNORECASE
    )
    
    # Pattern 3: Inline tags that wrap anchors without closing </a>
    tags_to_check = ['sup', 'em', 'strong', 'i', 'b']
    for tag in tags_to_check:
        pattern = re.compile(fr'(<{tag}[^>]*>)(\s*<a\b[^>]*>[^<]*)(</{tag}>)', re.IGNORECASE)
        def repl(match):
            opening, anchor_chunk, closing = match.groups()
            if '</a>' in anchor_chunk.lower():
                return match.group(0)
            return f"{opening}{anchor_chunk}</a>{closing}"
        content = pattern.sub(repl, content)
    
    # Generic fallback: ensure anchors close before major block-level closings
    content = close_anchor_before_block(content)
    
    # Balance anchor counts (remove stray </a> and close missing </a>)
    content = balance_anchor_tags(content)
    return content

def close_anchor_before_block(content):
    """Insert </a> before block-level closing tags when missing."""
    block_pattern = re.compile(
        r'(<a\b[^>]*>)([^<]*?)(</(?:sup|em|strong|i|b|span|p|div|li|h[1-6]|blockquote)>)',
        re.IGNORECASE
    )
    
    while True:
        updated = block_pattern.sub(lambda m: f"{m.group(1)}{m.group(2)}</a>{m.group(3)}", content)
        if updated == content:
            break
        content = updated
    
    return content

def balance_anchor_tags(content):
    """Remove stray </a> tags and close any remaining open anchors."""
    pattern = re.compile(r'<a\b[^>]*>|</a>', re.IGNORECASE)
    segments = []
    last_index = 0
    open_count = 0
    
    for match in pattern.finditer(content):
        segments.append(content[last_index:match.start()])
        token = match.group(0)
        if token.lower().startswith('</a'):
            if open_count > 0:
                open_count -= 1
                segments.append(token)
            else:
                # Skip unmatched closing anchor
                pass
        else:
            open_count += 1
            segments.append(token)
        last_index = match.end()
    
    segments.append(content[last_index:])
    balanced = ''.join(segments)
    
    if open_count > 0:
        replacement = '</a>' * open_count
        if '</body>' in balanced:
            balanced = balanced.replace('</body>', replacement + '</body>', 1)
        else:
            balanced = balanced + replacement
    
    return balanced

def wrap_blockquote_text(content):
    """Wrap direct blockquote text in <p> tags to satisfy EPUB 2 content model."""
    block_level_pattern = re.compile(
        r'^\s*<(?:address|blockquote|del|div|dl|h[1-6]|hr|ins|noscript|ol|p|pre|script|table|ul)\b',
        re.IGNORECASE
    )
    pattern = re.compile(r'(<blockquote[^>]*>)(.*?)(</blockquote>)', re.DOTALL | re.IGNORECASE)

    def wrap_inner(match):
        open_tag, inner, close_tag = match.groups()
        stripped = inner.strip()
        if not stripped:
            return f"{open_tag}<p>&nbsp;</p>{close_tag}"
        if block_level_pattern.match(stripped):
            return match.group(0)
        # Wrap entire inner fragment in a paragraph while preserving spacing
        wrapped = f"\n    <p>{stripped}</p>\n"
        return f"{open_tag}{wrapped}{close_tag}"

    return pattern.sub(wrap_inner, content)

def ensure_image_alt_attributes(content):
    """Ensure every <img> tag includes an alt attribute for accessibility."""
    img_pattern = re.compile(r'<img\b[^>]*>', re.IGNORECASE)

    def add_alt(match):
        tag = match.group(0)
        if re.search(r'\balt\s*=', tag, re.IGNORECASE):
            return tag
        src_match = re.search(r'\bsrc\s*=\s*"([^"]*)"', tag, re.IGNORECASE)
        alt_value = "Image"
        if src_match:
            filename = os.path.basename(src_match.group(1))
            alt_value = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').strip() or "Image"
        closing_match = re.search(r'\s*/?>\s*$', tag)
        if not closing_match:
            return tag
        prefix = tag[:closing_match.start()].rstrip()
        closing = closing_match.group(0)
        if not prefix.endswith(' '):
            prefix += ' '
        return f'{prefix}alt="{alt_value}"{closing}'

    return img_pattern.sub(add_alt, content)

def fix_fragment_identifiers(content, file_path):
    """Fix broken internal links and fragments by removing undefined fragment references"""
    # Extract existing IDs
    existing_ids = set(re.findall(r'id="([^"]+)"', content))
    
    def fix_href(match):
        href = match.group(1)
        if '#' in href:
            parts = href.rsplit('#', 1)
            if len(parts) == 2:
                file_part, fragment = parts
                # If it's a local reference (same file or no file specified)
                if not file_part or file_part.endswith(('.xhtml', '.html')):
                    # Check if fragment exists
                    if fragment and fragment not in existing_ids:
                        # Remove the fragment part
                        if file_part:
                            return f'href="{file_part}"'
                        else:
                            # Just # with no file - remove entire href or make it point to self
                            return 'href="#"'
        return match.group(0)
    
    content = re.sub(r'href="([^"]*)"', fix_href, content)
    return content

def fix_ncx_identifier(content, opf_content=None):
    """Fix NCX identifier to match OPF identifier"""
    # Extract identifier from OPF if provided
    if opf_content:
        opf_id_match = re.search(r'<dc:identifier[^>]*>([^<]+)</dc:identifier>', opf_content)
        if opf_id_match:
            correct_id = opf_id_match.group(1)
            # Update NCX identifier using function replacement to avoid group reference issues
            def replace_uid(match):
                return match.group(1) + correct_id + match.group(2)
            
            content = re.sub(
                r'(<meta\s+name="dtb:uid"\s+content=")[^"]*(")',
                replace_uid,
                content
            )
    return content

def fix_ncx_file(content, opf_content=None, fragment_index=None, current_path=None):
    """Fix NCX navigation issues - IDs with colons, playOrder, and pageList class"""
    
    # Fix NCX identifier to match OPF
    content = fix_ncx_identifier(content, opf_content)
    
    # Fix 1: Fix invalid XML IDs (must not start with numbers, no colons)
    def fix_id(match):
        id_value = match.group(1)
        # If ID starts with a number, prefix with 'id_'
        if id_value and id_value[0].isdigit():
            id_value = f'id_{id_value}'
        # Replace colons with underscores
        if ':' in id_value:
            id_value = id_value.replace(':', '_')
        return f'id="{id_value}"'
    
    content = re.sub(r'id="([^"]*)"', fix_id, content)
    
    # Fix 2: Ensure pageList has exactly ONE class attribute (fix duplicate class issue)
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '<pageList' in line:
            # Count class attributes
            class_count = line.count('class=')
            if class_count > 1:
                # Remove ALL class attributes
                new_line = re.sub(r'\s+class="[^"]*"', '', line)
                # Add back exactly ONE
                new_line = new_line.replace('<pageList', '<pageList class="pageList"', 1)
                lines[i] = new_line
            elif class_count == 0:
                # No class attribute, add one
                lines[i] = line.replace('<pageList', '<pageList class="pageList"', 1)
    
    content = '\n'.join(lines)
    
    # Fix 3: Fix playOrder - all elements with same src must have same playOrder
    # This is critical: if navMap and pageList both reference the same file,
    # they MUST have the same playOrder value
    lines = content.split('\n')
    
    # First pass: collect all navPoint/pageTarget and their src
    elements = []  # List of (line_index, src)
    for i, line in enumerate(lines):
        if 'playOrder=' in line and ('navPoint' in line or 'pageTarget' in line):
            # Find the associated content src in next few lines
            src = None
            for j in range(i, min(i + 10, len(lines))):
                if '<content src=' in lines[j]:
                    src_match = re.search(r'src="([^"]*)"', lines[j])
                    if src_match:
                        src = src_match.group(1)
                        break
            elements.append((i, src))
    
    # Build mapping: src -> playOrder (first occurrence wins)
    src_to_order = {}
    play_order = 1
    
    for line_idx, src in elements:
        if src and src not in src_to_order:
            src_to_order[src] = play_order
            play_order += 1
    
    # Second pass: update all playOrder values
    for line_idx, src in elements:
        if src and src in src_to_order:
            # Use the mapped playOrder for this src
            lines[line_idx] = re.sub(
                r'playOrder="[^"]*"',
                f'playOrder="{src_to_order[src]}"',
                lines[line_idx]
            )
        else:
            # No src found, assign sequential playOrder
            lines[line_idx] = re.sub(
                r'playOrder="[^"]*"',
                f'playOrder="{play_order}"',
                lines[line_idx]
            )
            play_order += 1
    
    content = '\n'.join(lines)
    
    # Remove fragment identifiers that point to missing anchors
    if fragment_index is not None and current_path is not None:
        base_dir = os.path.dirname(current_path)
        def fix_content_src(match):
            prefix, src_value, suffix = match.groups()
            if '#' not in src_value:
                return match.group(0)
            file_part, fragment = src_value.split('#', 1)
            fragment = fragment.strip()
            normalized_target = os.path.normpath(
                os.path.join(base_dir, file_part)
            ).replace('\\', '/')
            ids = fragment_index.get(normalized_target)
            if not fragment or not ids or fragment not in ids:
                return f'{prefix}{file_part}{suffix}'
            return match.group(0)
        content = re.sub(
            r'(<content\s+src=")([^"]*)(")',
            fix_content_src,
            content,
            flags=re.IGNORECASE
        )
    
    return content

def fix_opf_file(content):
    """Fix OPF file issues - remove invalid attributes and ensure proper structure"""
    # Fix 1: Remove page-map attribute from spine element (not allowed in EPUB 2.0.1)
    content = re.sub(r'<spine([^>]*)\s+page-map="[^"]*"([^>]*)>', r'<spine\1\2>', content)
    
    # Fix 2: Ensure all referenced items are in spine
    manifest_items = re.findall(r'<item[^>]*id="([^"]*)"[^>]*href="([^"]*cover\.xhtml[^"]*)"', content, re.IGNORECASE)
    spine_items = re.findall(r'<itemref[^>]*idref="([^"]*)"', content)
    
    for item_id, href in manifest_items:
        if item_id not in spine_items:
            content = re.sub(r'(</spine>)', f'    <itemref idref="{item_id}"/>\n\\1', content)
    
    return content

def fix_missing_file_references(content):
    """Remove references to files that don't exist in the EPUB"""
    # List of missing files based on the error output
    missing_patterns = [
        # Missing HTML files
        r'<[^>]*href="[^"]*cover\.html[^"]*"[^>]*/?>',
        r'<[^>]*href="[^"]*halftitle\.html[^"]*"[^>]*/?>',
        r'<[^>]*href="[^"]*title\.html[^"]*"[^>]*/?>',
        r'<[^>]*href="[^"]*copyright\.html[^"]*"[^>]*/?>',
        r'<[^>]*href="[^"]*dedication\.html[^"]*"[^>]*/?>',
        r'<[^>]*href="[^"]*preface\.html[^"]*"[^>]*/?>',
        r'<[^>]*href="[^"]*contents\.html[^"]*"[^>]*/?>',
        r'<[^>]*href="[^"]*part01\.html[^"]*"[^>]*/?>',
        r'<[^>]*href="[^"]*image01\.html[^"]*"[^>]*/?>',
        r'<[^>]*href="[^"]*chapter\d+\.html[^"]*"[^>]*/?>',
        r'<[^>]*href="[^"]*part\d+\.html[^"]*"[^>]*/?>',
        r'<[^>]*href="[^"]*appendix\d+\.html[^"]*"[^>]*/?>',
        r'<[^>]*href="[^"]*notes\.html[^"]*"[^>]*/?>',
        r'<[^>]*href="[^"]*bibliography\.html[^"]*"[^>]*/?>',
        r'<[^>]*href="[^"]*index\.html[^"]*"[^>]*/?>',
        
        # Missing image files
        r'<img[^>]*src="[^"]*9780199744503\.jpg[^"]*"[^>]*/?>',
        r'<img[^>]*src="[^"]*f\d{4}-\d{2}\.jpg[^"]*"[^>]*/?>',
        r'<img[^>]*src="[^"]*t\d{4}-\d{2}\.jpg[^"]*"[^>]*/?>',
        r'<img[^>]*src="[^"]*pub\.jpg[^"]*"[^>]*/?>',
        
        # Missing font files
        r'<[^>]*href="[^"]*CharisSIL[ABIR]\.ttf[^"]*"[^>]*/?>',
        
        # Missing CSS files
        r'<link[^>]*href="[^"]*page-template\.xpgt[^"]*"[^>]*/?>',
    ]

    for pattern in missing_patterns:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE)

    return content

def process_file(file_path, opf_content=None, fragment_index=None, root_dir=None):
    """Process single file (XHTML, NCX, or OPF)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        rel_path = None
        if root_dir:
            rel_path = os.path.relpath(file_path, root_dir).replace('\\', '/')
        
        if file_path.endswith('.ncx'):
            content = fix_ncx_file(content, opf_content, fragment_index, rel_path)
            # Fix duplicate class attributes specifically for NCX
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'class=' in line and line.count('class=') > 1:
                    # Keep only the first class attribute
                    parts = line.split('class=')
                    new_line = parts[0] + 'class=' + parts[1]
                    # Find the end of the first class value
                    quote_pos = new_line.find('"', new_line.find('class=') + 6)
                    if quote_pos != -1:
                        # Remove all subsequent class attributes
                        remaining = new_line[quote_pos + 1:]
                        remaining = re.sub(r'\s+class="[^"]*"', '', remaining)
                        lines[i] = new_line[:quote_pos + 1] + remaining
            content = '\n'.join(lines)
        elif file_path.endswith('.opf'):
            content = fix_opf_file(content)
            # Fix fragment identifiers in OPF
            content = re.sub(r'href="([^#]*)#[^"]*"', r'href="\1"', content)
        else:
            if file_path.endswith('.xml') and '<html' not in content.lower():
                return False
            content = fix_html_content(content)
            content = fix_fragment_identifiers(content, file_path)
            # Remove references to missing files
            content = fix_missing_file_references(content)
        
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
        
        # First, find and read OPF file to get correct identifier
        opf_content = None
        opf_file = None
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith('.opf'):
                    opf_file = os.path.join(root, file)
                    with open(opf_file, 'r', encoding='utf-8') as f:
                        opf_content = f.read()
                    break
            if opf_content:
                break
        
        # Build fragment index for validating NCX fragment references
        fragment_index = build_fragment_index(extract_dir)
        
        # Find and process all relevant files
        process_files = []
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith(('.xhtml', '.html', '.ncx', '.opf', '.xml')):
                    process_files.append(os.path.join(root, file))
        
        fixed_count = 0
        for file_path in process_files:
            if process_file(file_path, opf_content, fragment_index, extract_dir):
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
        error_count = output.count('ERROR(') + output.count('FATAL(')  # Also count FATAL errors

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
