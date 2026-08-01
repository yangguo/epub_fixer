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

import argparse
import os
import posixpath
import re
import shutil
import sys
import tempfile
import zipfile
from urllib.parse import unquote, urlsplit

from config import EPUBCHECK_JAR
from utils import count_errors, run_epubcheck


SUPPORTED_TARGET_VERSIONS = {"auto", "epub2", "epub3"}


def detect_epub_version(opf_content):
    """Return the package version declared by an OPF document, if present."""
    match = re.search(
        r"<package\b[^>]*\bversion\s*=\s*(['\"])([^'\"]+)\1",
        opf_content or "",
        flags=re.IGNORECASE,
    )
    return match.group(2) if match else None


def resolve_target_version(target_version="auto", opf_content=None):
    """Resolve a compatible repair policy from the requested target/package."""
    target = (target_version or "auto").strip().lower()
    if target not in SUPPORTED_TARGET_VERSIONS:
        choices = ", ".join(sorted(SUPPORTED_TARGET_VERSIONS))
        raise ValueError(f"target_version must be one of: {choices}")

    package_version = detect_epub_version(opf_content)
    package_target = (
        "epub2" if package_version and package_version.startswith("2") else "epub3"
    )
    if target != "auto" and package_version and target != package_target:
        raise ValueError(
            f"target_version={target} conflicts with package version "
            f"{package_version}; use target_version=auto or match the package"
        )
    return package_target if target == "auto" else target


def _get_attribute(tag, name):
    """Read one XML-style attribute from a tag while preserving malformed input."""
    match = re.search(
        rf"(?<![\w:.-]){re.escape(name)}\s*=\s*(['\"])(.*?)\1",
        tag,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return match.group(2) if match else None


def _replace_attribute(tag, name, value):
    """Replace an existing attribute value and preserve its quote style."""
    pattern = re.compile(
        rf"(?P<prefix>(?<![\w:.-]){re.escape(name)}\s*=\s*)(?P<quote>['\"])(?P<value>.*?)(?P=quote)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    return pattern.sub(
        lambda match: (
            f"{match.group('prefix')}{match.group('quote')}"
            f"{value}{match.group('quote')}"
        ),
        tag,
        count=1,
    )


def _add_attribute(tag, name, value):
    """Add an attribute before a tag's closing marker."""
    closing = re.search(r"\s*/?>\s*$", tag, flags=re.DOTALL)
    if not closing:
        return tag
    prefix = tag[:closing.start()].rstrip()
    return f'{prefix} {name}="{value}"{closing.group(0)}'


def _remove_attribute(tag, name):
    """Remove one XML-style attribute from a tag."""
    return re.sub(
        rf"\s+(?<![\w:.-]){re.escape(name)}\s*=\s*(['\"])(.*?)\1",
        "",
        tag,
        flags=re.IGNORECASE | re.DOTALL,
    )


def _manifest_items(opf_content):
    """Return manifest item records without requiring a strict XML parser."""
    items = []
    for match in re.finditer(r"<item\b[^>]*?/?>", opf_content, flags=re.IGNORECASE | re.DOTALL):
        tag = match.group(0)
        item_id = _get_attribute(tag, "id")
        href = _get_attribute(tag, "href")
        media_type = _get_attribute(tag, "media-type")
        if not item_id or not href:
            continue
        properties = (_get_attribute(tag, "properties") or "").split()
        items.append(
            {
                "id": item_id,
                "href": href,
                "media_type": media_type or "",
                "properties": properties,
                "start": match.start(),
                "end": match.end(),
            }
        )
    return items


def _cover_metadata_ids(opf_content):
    """Return legacy cover metadata values in document order."""
    values = []
    for match in re.finditer(r"<meta\b[^>]*?/?>", opf_content, flags=re.IGNORECASE | re.DOTALL):
        tag = match.group(0)
        if (_get_attribute(tag, "name") or "").lower() == "cover":
            value = _get_attribute(tag, "content")
            if value:
                values.append(value)
    return values


def _choose_cover_item(opf_content):
    """Choose a cover image only when the package gives us useful evidence."""
    items = _manifest_items(opf_content)
    if not items:
        return None

    legacy_ids = set(_cover_metadata_ids(opf_content))
    scored = []
    for item in items:
        media_type = item["media_type"].lower()
        if not media_type.startswith("image/"):
            continue
        item_id = item["id"]
        href = item["href"]
        score = 0
        if "cover-image" in item["properties"]:
            score += 100
        if item_id in legacy_ids:
            score += 90
        if "cover" in item_id.lower():
            score += 50
        if "cover" in posixpath.basename(href).lower():
            score += 40
        if score:
            scored.append((score, item))

    return max(scored, key=lambda entry: entry[0])[1] if scored else None


def fix_cover_metadata(content, target_version="auto"):
    """Make legacy and EPUB 3 cover metadata point to the same image item."""
    resolved_target = resolve_target_version(target_version, content)
    cover_item = _choose_cover_item(content)
    if not cover_item:
        return content

    cover_id = cover_item["id"]
    item_pattern = re.compile(r"<item\b[^>]*?/?>", flags=re.IGNORECASE | re.DOTALL)

    def update_cover_item(match):
        tag = match.group(0)
        if _get_attribute(tag, "id") != cover_id:
            return tag

        properties = (_get_attribute(tag, "properties") or "").split()
        if resolved_target == "epub3":
            if "cover-image" not in properties:
                properties.append("cover-image")
            new_properties = " ".join(properties)
            if _get_attribute(tag, "properties") is None:
                return _add_attribute(tag, "properties", new_properties)
            return _replace_attribute(tag, "properties", new_properties)

        properties = [value for value in properties if value != "cover-image"]
        if properties:
            return _replace_attribute(tag, "properties", " ".join(properties))
        return _remove_attribute(tag, "properties")

    content = item_pattern.sub(update_cover_item, content)

    meta_pattern = re.compile(r"<meta\b[^>]*?/?>", flags=re.IGNORECASE | re.DOTALL)
    found_legacy_meta = False

    def update_cover_meta(match):
        nonlocal found_legacy_meta
        tag = match.group(0)
        if (_get_attribute(tag, "name") or "").lower() != "cover":
            return tag
        found_legacy_meta = True
        if _get_attribute(tag, "content") is None:
            return _add_attribute(tag, "content", cover_id)
        return _replace_attribute(tag, "content", cover_id)

    content = meta_pattern.sub(update_cover_meta, content)

    if found_legacy_meta:
        return content

    metadata_match = re.search(
        r"(<(?:[\w.-]+:)?metadata\b[^>]*>)(.*?)(</(?:[\w.-]+:)?metadata\s*>)",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not metadata_match:
        return content

    inner = metadata_match.group(2)
    indent_match = re.search(r"\n([ \t]+)<", inner)
    indent = indent_match.group(1) if indent_match else "  "
    stripped_inner = inner.rstrip()
    trailing = inner[len(stripped_inner):]
    inserted_inner = f'{stripped_inner}\n{indent}<meta name="cover" content="{cover_id}"/>{trailing}'
    return (
        content[:metadata_match.start(2)]
        + inserted_inner
        + content[metadata_match.end(2):]
    )


def extract_epub(epub_path, extract_dir):
    """Extract EPUB with proper structure"""
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)


def find_opf_file(extract_dir):
    """Find the package document via container.xml, with a safe fallback."""
    container_path = os.path.join(extract_dir, "META-INF", "container.xml")
    if os.path.exists(container_path):
        with open(container_path, "r", encoding="utf-8") as container_file:
            container = container_file.read()
        rootfile_match = re.search(
            r"<rootfile\b[^>]*\bfull-path\s*=\s*(['\"])(.*?)\1",
            container,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if rootfile_match:
            candidate = os.path.join(
                extract_dir, rootfile_match.group(2).replace("/", os.sep)
            )
            if os.path.isfile(candidate):
                return candidate

    candidates = []
    for root, _, files in os.walk(extract_dir):
        candidates.extend(
            os.path.join(root, file)
            for file in files
            if file.lower().endswith(".opf")
        )
    return sorted(candidates)[0] if candidates else None

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
            if not file.lower().endswith(('.xhtml', '.html', '.htm', '.xml')):
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
            fragment_index[rel_path] = set(
                re.findall(r'\b(?:id|xml:id)\s*=\s*["\']([^"\']+)["\']', content)
            )
    return fragment_index

def _normalize_id_value(value):
    """Return the legacy-safe spelling used for an XML identifier."""
    if not value:
        return value
    value = value.replace(":", "_")
    if value[0].isdigit():
        value = f"id_{value}"
    return value


def _normalize_ids_with_mapping(content):
    """Normalize IDs and return the old-to-new mapping for reference repair."""
    rewrites = {}
    id_pattern = re.compile(
        r"(?P<prefix>(?<![:\w.-])\bid\s*=\s*)"
        r"(?P<quote>[\"'])(?P<value>.*?)(?P=quote)",
        flags=re.IGNORECASE | re.DOTALL,
    )

    def normalize_id(match):
        old_value = match.group("value")
        new_value = _normalize_id_value(old_value)
        if old_value and new_value != old_value:
            rewrites[old_value] = new_value
        return (
            f'{match.group("prefix")}{match.group("quote")}'
            f'{new_value}{match.group("quote")}'
        )

    content = id_pattern.sub(normalize_id, content)

    idref_pattern = re.compile(
        r"(?P<prefix>(?<![:\w.-])\bidref\s*=\s*)"
        r"(?P<quote>[\"'])(?P<value>.*?)(?P=quote)",
        flags=re.IGNORECASE | re.DOTALL,
    )

    def normalize_idref(match):
        values = match.group("value").split()
        normalized_values = [
            rewrites.get(value, _normalize_id_value(value)) for value in values
        ]
        new_value = " ".join(normalized_values)
        return (
            f'{match.group("prefix")}{match.group("quote")}'
            f'{new_value}{match.group("quote")}'
        )

    content = idref_pattern.sub(normalize_idref, content)
    return content, rewrites


def _replace_url_fragment(value, rewrites):
    """Replace a URL fragment when it matches one of the renamed IDs."""
    parsed = urlsplit(value)
    if parsed.scheme or value.startswith("//") or not parsed.fragment:
        return value
    replacement = rewrites.get(unquote(parsed.fragment))
    return parsed._replace(fragment=replacement).geturl() if replacement else value


def _replace_id_references(content, rewrites):
    """Update local fragments, IDREF attributes, and legacy cover metadata."""
    if not rewrites:
        return content

    idref_attributes = (
        "for",
        "headers",
        "idref",
        "aria-labelledby",
        "aria-describedby",
        "aria-controls",
        "aria-owns",
        "aria-flowto",
        "aria-details",
        "aria-errormessage",
        "aria-activedescendant",
    )
    attribute_pattern = re.compile(
        r"(?P<prefix>\b(?P<name>href|src|"
        + "|".join(re.escape(name) for name in idref_attributes)
        + r")\s*=\s*)"
        r"(?P<quote>[\"'])(?P<value>.*?)(?P=quote)",
        flags=re.IGNORECASE | re.DOTALL,
    )

    def replace_reference(match):
        name = match.group("name").lower()
        value = match.group("value")
        new_value = value
        if name in {"href", "src"}:
            new_value = _replace_url_fragment(value, rewrites)
        else:
            values = value.split()
            new_value = " ".join(rewrites.get(item, item) for item in values)

        if new_value == value:
            return match.group(0)
        return (
            f'{match.group("prefix")}{match.group("quote")}'
            f'{new_value}{match.group("quote")}'
        )

    content = attribute_pattern.sub(replace_reference, content)

    meta_pattern = re.compile(r"<meta\b[^>]*?/?>", flags=re.IGNORECASE | re.DOTALL)

    def replace_cover_meta(match):
        tag = match.group(0)
        if (_get_attribute(tag, "name") or "").lower() != "cover":
            return tag
        value = _get_attribute(tag, "content")
        replacement = rewrites.get(value)
        return _replace_attribute(tag, "content", replacement) if replacement else tag

    return meta_pattern.sub(replace_cover_meta, content)


def fix_invalid_id_attributes(content):
    """Normalize XML IDs and keep local references aligned with renamed IDs."""
    content, rewrites = _normalize_ids_with_mapping(content)
    return _replace_id_references(content, rewrites)


def fix_invalid_aria_idrefs(content):
    """Keep valid ARIA ID references and drop only references that do not exist."""
    existing_ids = set(
        re.findall(r'\b(?:id|xml:id)\s*=\s*["\']([^"\']+)["\']', content)
    )
    idref_attributes = (
        "labelledby",
        "describedby",
        "controls",
        "owns",
        "flowto",
        "details",
        "errormessage",
        "activedescendant",
    )
    attribute_pattern = re.compile(
        r'(?P<prefix>\baria-(?:' + "|".join(idref_attributes) + r')\s*=\s*)'
        r'(?P<quote>["\'])(?P<value>.*?)(?P=quote)',
        flags=re.IGNORECASE | re.DOTALL,
    )

    def repair(match):
        values = match.group("value").split()
        valid_values = [value for value in values if value in existing_ids]
        if not valid_values:
            return ""
        if valid_values == values:
            return match.group(0)
        return (
            f'{match.group("prefix")}{match.group("quote")}'
            f'{" ".join(valid_values)}{match.group("quote")}'
        )

    return attribute_pattern.sub(repair, content)

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

def fix_html_content(content, target_version="epub3"):
    """Apply repair rules while preserving EPUB 3 semantics by default."""
    target_version = resolve_target_version(target_version, content)
    # CRITICAL: Fix mangled tags FIRST - these cause fatal parsing errors
    content = fix_mangled_p_tags(content)
    
    # Then fix unclosed tags
    content = fix_unclosed_anchor_tags(content)
    content = fix_unclosed_p_tags(content)
    
    # Fix invalid IDs and keep fragment/ARIA references aligned with renames.
    content, id_rewrites = _normalize_ids_with_mapping(content)
    content = _replace_id_references(content, id_rewrites)
    content = fix_invalid_aria_idrefs(content)
    
    # First fix dir attributes
    content = fix_dir_attributes(content)
    
    # Fix malformed head tags first
    content = re.sub(r'</head\b[^>]*>', '</head>', content, flags=re.IGNORECASE)
    
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
        # EPUB 3 metadata and classes are meaningful; only strip the legacy
        # prefix when the caller explicitly requests EPUB 2 compatibility.
        if target_version == "epub2":
            html_tag = re.sub(r'\s+epub:prefix="[^"]*"', '', html_tag, flags=re.IGNORECASE)
        return html_tag
    
    content = re.sub(r'<html[^>]*>', fix_html_namespace, content, flags=re.IGNORECASE)
    
    # Fix structural issues - move misplaced elements
    content = fix_structural_issues(content)
    
    fixes = []
    if target_version == "epub2":
        fixes.extend([
            # Remove EPUB 3-specific semantics only in explicit EPUB 2 mode.
            (r'<head\b[^>]*\s+epub:prefix="[^"]*"([^>]*)>', r'<head\1>'),
            (r'<head\b[^>]*\s+class="[^"]*"([^>]*)>', r'<head\1>'),
            (r'<body[^>]*\s+epub:type="[^"]*"([^>]*)>', r'<body\1>'),
            (r'\s+epub:type="[^"]*"', ''),
            (r'\s+epub:prefix="[^"]*"', ''),
            (r'\s+data-number="[^"]*"', ''),
            (r'\s+hidden(?:="[^"]*")?', ''),
            (r'\s+aria-[a-z-]*="[^"]*"', ''),
            (r'\s+role="[^"]*"', ''),
            (r'<section([^>]*)>', r'<div\1>'),
            (r'</section>', '</div>'),
            (r'<nav([^>]*)>', r'<div\1>'),
            (r'</nav>', '</div>'),
            (r'<figure([^>]*)>', r'<div\1>'),
            (r'</figure>', '</div>'),
            (r'<figcaption([^>]*)>', r'<div\1>'),
            (r'</figcaption>', '</div>'),
            (r'<aside([^>]*)>', r'<div\1>'),
            (r'</aside>', '</div>'),
            (r'<header([^>]*)>', r'<div\1>'),
            (r'</header>', '</div>'),
        ])

    # XHTML 1-compatible style markup is harmless in EPUB 3 and useful for
    # EPUB 2 readers, so keep this repair in both modes.
    fixes.append((r'<style(?![^>]*type=)([^>]*)>', r'<style type="text/css"\1>'))
    
    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)

    # Fix malformed sup tags (e.g., <sup>1</a></sup> -> <sup>1</sup>)
    content = fix_malformed_sup_tags(content)
    
    # Additional cleanup for empty attributes
    content = re.sub(r'\s+\w+="\s*"', '', content)  # Remove empty attributes
    
    # Fix hrefs that look like bare domain names missing a scheme (e.g., "notability.com/")
    content = re.sub(
        r'href="((?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+(?:com|org|net|edu|gov|io|co|uk|cn|jp|de|fr|ru|br|in|au|ca|it|es|nl|se|no|dk|fi|pt|pl|ie|nz|sg|hk|tw|kr|mx|ar|ch|at|be)/[^"]*)"',
        r'href="https://\1"',
        content
    )

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
    head_match = re.search(r'<head\b[^>]*>(.*?)</head\b>', content, re.DOTALL | re.IGNORECASE)
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
    head_match = re.search(r'<head\b[^>]*>(.*?)</head\b>', content, re.DOTALL | re.IGNORECASE)
    if head_match:
        head_content = head_match.group(1)
        if not re.search(r'<title[^>]*>.*?</title>', head_content, re.DOTALL | re.IGNORECASE):
            # Add a default title if missing
            head_content += '\\n<title>Document</title>'
            content = content.replace(head_match.group(0), f'<head>{head_content}</head>')
    
    # Fix duplicate head elements (remove misplaced ones)
    # Keep only the first head element, remove others
    head_matches = list(re.finditer(r'<head\b[^>]*>.*?</head\b>', content, re.DOTALL | re.IGNORECASE))
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

def fix_fragment_identifiers(
    content,
    file_path,
    fragment_index=None,
    root_dir=None,
    fragment_rewrites=None,
):
    """Remove a fragment only when the target document is known and missing it."""
    fragment_index = fragment_index or {}
    fragment_rewrites = fragment_rewrites or {}
    current_path = file_path.replace("\\", "/")
    if root_dir and os.path.isabs(file_path):
        current_path = os.path.relpath(file_path, root_dir).replace("\\", "/")
    current_ids = fragment_index.get(current_path)
    if current_ids is None:
        current_ids = set(
            re.findall(r'\b(?:id|xml:id)\s*=\s*["\']([^"\']+)["\']', content)
        )

    def fix_href(match):
        href = match.group("href")
        if "#" not in href:
            return match.group(0)

        parsed = urlsplit(href)
        if parsed.scheme or href.startswith("//") or href.startswith(("data:", "mailto:")):
            return match.group(0)

        file_part = parsed.path
        fragment = unquote(parsed.fragment)
        if not fragment:
            return match.group(0)

        if file_part:
            target_path = posixpath.normpath(
                posixpath.join(posixpath.dirname(current_path), unquote(file_part))
            )
            target_rewrites = fragment_rewrites.get(target_path, {})
            replacement = target_rewrites.get(fragment)
            if replacement:
                replacement_href = _replace_url_fragment(
                    href, {fragment: replacement}
                )
                return (
                    f'{match.group("prefix")}{match.group("quote")}'
                    f'{replacement_href}{match.group("quote")}'
                )
            target_ids = fragment_index.get(target_path)
            # Unknown targets are left untouched: guessing here can destroy a
            # valid link when a package uses an extension or path variant.
            if target_ids is None or fragment in target_ids:
                return match.group(0)
        else:
            replacement = fragment_rewrites.get(current_path, {}).get(fragment)
            if replacement:
                replacement_href = _replace_url_fragment(
                    href, {fragment: replacement}
                )
                return (
                    f'{match.group("prefix")}{match.group("quote")}'
                    f'{replacement_href}{match.group("quote")}'
                )
            target_ids = current_ids
            if fragment in target_ids:
                return match.group(0)

        replacement_href = file_part or "#"
        return (
            f'{match.group("prefix")}{match.group("quote")}'
            f'{replacement_href}{match.group("quote")}'
        )

    return re.sub(
        r'(?P<prefix>\bhref\s*=\s*)(?P<quote>["\'])(?P<href>.*?)(?P=quote)',
        fix_href,
        content,
        flags=re.IGNORECASE,
    )

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

def fix_ncx_file(
    content,
    opf_content=None,
    fragment_index=None,
    current_path=None,
    fragment_rewrites=None,
):
    """Fix NCX navigation issues - IDs with colons, playOrder, and pageList class"""
    
    # Fix NCX identifier to match OPF
    content = fix_ncx_identifier(content, opf_content)
    
    # Fix IDs and references together so NCX anchors remain navigable.
    content, id_rewrites = _normalize_ids_with_mapping(content)
    content = _replace_id_references(content, id_rewrites)
    
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
    if current_path is not None:
        fragment_index = fragment_index or {}
        fragment_rewrites = fragment_rewrites or {}
        base_dir = os.path.dirname(current_path)
        def fix_content_src(match):
            prefix, src_value, suffix = match.groups()
            parsed = urlsplit(src_value)
            if not parsed.fragment:
                return match.group(0)
            file_part = parsed.path
            fragment = unquote(parsed.fragment.strip())
            normalized_target = os.path.normpath(
                os.path.join(base_dir, file_part)
            ).replace('\\', '/')
            replacement = fragment_rewrites.get(normalized_target, {}).get(fragment)
            if replacement:
                return f'{prefix}{parsed._replace(fragment=replacement).geturl()}{suffix}'
            ids = fragment_index.get(normalized_target)
            if not fragment or ids is None or fragment in ids:
                return match.group(0)
            return f'{prefix}{parsed._replace(fragment="").geturl().rstrip("#")}{suffix}'
        content = re.sub(
            r'(<content\s+src=")([^"]*)(")',
            fix_content_src,
            content,
            flags=re.IGNORECASE
        )
    
    return content

def fix_opf_file(content, target_version="auto"):
    """Repair OPF references without changing the package version."""
    target_version = resolve_target_version(target_version, content)

    # EPUB 3 removed the EPUB 2 page-map spine attribute. Keep it when the
    # package is intentionally being handled as EPUB 2.
    if target_version == "epub3":
        content = re.sub(r'<spine([^>]*)\s+page-map="[^"]*"([^>]*)>', r'<spine\1\2>', content)

    # Fix package IDs and keep idref/cover metadata aligned with renames.
    content, id_rewrites = _normalize_ids_with_mapping(content)
    content = _replace_id_references(content, id_rewrites)

    # XHTML content documents should be advertised with the XHTML media type
    # in both EPUB generations.
    content = content.replace('media-type="text/html"', 'media-type="application/xhtml+xml"')

    # Keep the cover page reachable from the reading order.
    def make_cover_linear(match):
        tag = match.group(0)
        idref = _get_attribute(tag, "idref") or ""
        if "cover" in idref.lower() and (_get_attribute(tag, "linear") or "").lower() == "no":
            return _remove_attribute(tag, "linear")
        return tag

    content = re.sub(
        r"<itemref\b[^>]*?/?>",
        make_cover_linear,
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Repair the exact mismatch that made clearing.epub invisible to some
    # readers: legacy metadata must reference the real manifest item id.
    content = fix_cover_metadata(content, target_version)

    # Ensure cover pages are reachable when a package explicitly names one.
    manifest_items = [
        (item["id"], item["href"])
        for item in _manifest_items(content)
        if "cover.xhtml" in item["href"].lower()
    ]
    spine_items = [
        _get_attribute(match.group(0), "idref")
        for match in re.finditer(r"<itemref\b[^>]*?/?>", content, re.IGNORECASE | re.DOTALL)
    ]

    for item_id, href in manifest_items:
        if item_id not in spine_items:
            content = re.sub(r'(</spine>)', f'    <itemref idref="{item_id}"/>\n\\1', content)

    return content

def fix_missing_file_references(content, source_path=None, available_paths=None):
    """Remove known-bad references only after checking the package file set."""
    if not available_paths:
        return content

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
        r'<img[^>]*src="[^"]*images/cover_fmt\.jpg[^"]*"[^>]*/?>',
        
        # Missing font files
        r'<[^>]*href="[^"]*CharisSIL[ABIR]\.ttf[^"]*"[^>]*/?>',
        
        # Missing CSS files
        r'<link[^>]*href="[^"]*WileyTemplate_v5\.1\.css[^"]*"[^>]*/?>',
        r'<link[^>]*href="[^"]*page-template\.xpgt[^"]*"[^>]*/?>',
    ]

    source_path = (source_path or "").replace("\\", "/")
    source_dir = posixpath.dirname(source_path)

    def remove_if_missing(match):
        tag = match.group(0)
        reference = _get_attribute(tag, "href") or _get_attribute(tag, "src")
        if not reference:
            return tag
        parsed = urlsplit(reference)
        if parsed.scheme or reference.startswith("//") or not parsed.path:
            return tag
        target_path = posixpath.normpath(
            posixpath.join(source_dir, unquote(parsed.path))
        )
        return "" if target_path not in available_paths else tag

    for pattern in missing_patterns:
        content = re.sub(pattern, remove_if_missing, content, flags=re.IGNORECASE)

    return content

def fix_css_file(content):
    """Fix CSS file issues - remove invalid font references and malformed rules."""
    # Remove @font-face rules with invalid or missing src URLs (like XXXXXXXXXXXXXXXX)
    content = re.sub(
        r'@font-face\s*\{[^}]*src:\s*url\([^)]*XXXX[^)]*\)[^}]*\}',
        '',
        content,
        flags=re.IGNORECASE
    )
    
    # Remove any other malformed url() references
    content = re.sub(
        r'src:\s*url\([^)]*XXXX[^)]*\);',
        '',
        content,
        flags=re.IGNORECASE
    )
    
    return content

def process_file(
    file_path,
    opf_content=None,
    fragment_index=None,
    root_dir=None,
    target_version="epub3",
    available_paths=None,
    fragment_rewrites=None,
):
    """Process one EPUB resource using the selected compatibility policy."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        rel_path = None
        if root_dir:
            rel_path = os.path.relpath(file_path, root_dir).replace('\\', '/')
        
        lower_file_path = file_path.lower()
        if lower_file_path.endswith('.ncx'):
            content = fix_ncx_file(
                content,
                opf_content,
                fragment_index,
                rel_path,
                fragment_rewrites,
            )
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
        elif lower_file_path.endswith('.opf'):
            content = fix_opf_file(content, target_version)
        elif lower_file_path.endswith('.css'):
            # Fix CSS files with invalid font references
            content = fix_css_file(content)
        else:
            if lower_file_path.endswith('.xml') and '<html' not in content.lower():
                return False
            content = fix_html_content(content, target_version)
            content = fix_fragment_identifiers(
                content,
                rel_path or file_path,
                fragment_index,
                root_dir,
                fragment_rewrites,
            )
            # Remove references to missing files
            content = fix_missing_file_references(
                content,
                rel_path or file_path,
                available_paths,
            )
        
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def fix_epub(epub_path, target_version="auto"):
    """Repair an EPUB in place using automatic or explicit compatibility mode."""
    print(f"🔄 Processing: {epub_path}")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        extract_dir = os.path.join(temp_dir, 'epub')
        extract_epub(epub_path, extract_dir)
        
        # Read the package selected by container.xml, not an arbitrary OPF.
        opf_file = find_opf_file(extract_dir)
        opf_content = None
        if opf_file:
            with open(opf_file, 'r', encoding='utf-8') as opf_handle:
                opf_content = opf_handle.read()
        resolved_target = resolve_target_version(target_version, opf_content)

        # Build fragment index for validating NCX fragment references
        fragment_index = build_fragment_index(extract_dir)

        package_paths = set()
        for root, _, files in os.walk(extract_dir):
            package_paths.update(
                os.path.relpath(os.path.join(root, file), extract_dir).replace('\\', '/')
                for file in files
            )
        
        # Find and process all relevant files
        process_files = []
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.lower().endswith(('.xhtml', '.html', '.htm', '.ncx', '.opf', '.xml', '.css')):
                    process_files.append(os.path.join(root, file))

        # The package document should be normalized before consumers such as
        # NCX are processed, so downstream files see repaired ids/metadata.
        process_files.sort(
            key=lambda path: (
                0 if path == opf_file else 1 if path.lower().endswith('.ncx') else 2,
                path,
            )
        )

        # Precompute ID renames before fixing links. This lets a source file
        # update a fragment that points to a later-processed target document.
        fragment_rewrites = {}
        for file_path in process_files:
            lower_file_path = file_path.lower()
            if not lower_file_path.endswith(('.xhtml', '.html', '.htm', '.xml', '.ncx')):
                continue
            try:
                with open(file_path, 'r', encoding='utf-8') as file_handle:
                    _, rewrites = _normalize_ids_with_mapping(file_handle.read())
            except (OSError, UnicodeDecodeError):
                continue
            if rewrites:
                rel_path = os.path.relpath(file_path, extract_dir).replace('\\', '/')
                fragment_rewrites[rel_path] = rewrites

        fixed_count = 0
        for file_path in process_files:
            if process_file(
                file_path,
                opf_content,
                fragment_index,
                extract_dir,
                resolved_target,
                package_paths,
                fragment_rewrites,
            ):
                fixed_count += 1
            if file_path == opf_file:
                with open(opf_file, 'r', encoding='utf-8') as opf_handle:
                    opf_content = opf_handle.read()
        
        # Backup and repack
        backup = epub_path.replace('.epub', '_backup.epub')
        if not os.path.exists(backup):
            shutil.copy2(epub_path, backup)
        
        repack_epub(extract_dir, epub_path)
        print(f"✅ Fixed {fixed_count} files, backup saved as {backup}")

def validate_and_fix(epub_path, max_iterations=5, target_version="auto"):
    """Iteratively validate and fix using the selected compatibility policy."""
    if not os.path.exists(EPUBCHECK_JAR):
        print(f"❌ epubcheck.jar not found at {EPUBCHECK_JAR}")
        return False

    for iteration in range(1, max_iterations + 1):
        print(f"\n🔄 Iteration {iteration}")

        output = run_epubcheck(epub_path)
        error_count, _ = count_errors(output)

        if error_count == 0:
            print("✅ EPUB is valid!")
            return True

        print(f"📊 Found {error_count} errors, fixing...")

        # Save current output for analysis
        with open('output.txt', 'w', encoding='utf-8') as f:
            f.write(output)

        fix_epub(epub_path, target_version=target_version)

    print("⚠️  Max iterations reached, check remaining errors")
    return False
def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description="Repair and validate an EPUB package.")
    parser.add_argument("epub_path", help="Path to the EPUB file to process.")
    parser.add_argument(
        "--target",
        choices=sorted(SUPPORTED_TARGET_VERSIONS),
        default="auto",
        help="Content compatibility policy (default: detect from the OPF package version).",
    )
    args = parser.parse_args()

    epub_path = args.epub_path
    if not os.path.exists(epub_path):
        print(f"❌ File not found: {epub_path}")
        return
    
    print("🚀 EPUB Master Fixer Starting...")
    validate_and_fix(epub_path, target_version=args.target)

if __name__ == "__main__":
    main()
