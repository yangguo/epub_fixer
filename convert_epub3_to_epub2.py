#!/usr/bin/env python3
"""
EPUB 3 to EPUB 2 Converter
This script converts an EPUB 3 file to EPUB 2.0.1 format by:
1. Updating the OPF file to use EPUB 2 specifications
2. Converting navigation document to NCX format
3. Removing EPUB 3 specific features from content files
4. Ensuring EPUB 2 compatibility
"""

import os
import re
import zipfile
import shutil
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
from xml.dom import minidom

def extract_epub(epub_path, extract_dir):
    """Extract EPUB file to directory"""
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print(f"Extracted EPUB to: {extract_dir}")

def create_epub_from_directory(source_dir, output_path):
    """Create EPUB file from directory with proper structure"""
    source_path = Path(source_dir)
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # First, add mimetype without compression
        mimetype_path = source_path / 'mimetype'
        if mimetype_path.exists():
            zip_file.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files with compression
        for root, dirs, files in os.walk(source_path):
            for file in files:
                if file == 'mimetype':
                    continue  # Already added
                    
                file_path = Path(root) / file
                archive_path = str(file_path.relative_to(source_path)).replace('\\', '/')
                zip_file.write(file_path, archive_path)
    
    print(f"Created EPUB: {output_path}")

def find_opf_file(work_dir):
    """Find the OPF file in the EPUB structure"""
    # Check container.xml for OPF location
    container_path = work_dir / "META-INF" / "container.xml"
    if container_path.exists():
        try:
            tree = ET.parse(container_path)
            root = tree.getroot()
            # Find rootfile element
            for rootfile in root.iter():
                if rootfile.tag.endswith('rootfile'):
                    opf_path = rootfile.get('full-path')
                    if opf_path:
                        return work_dir / opf_path
        except Exception as e:
            print(f"Error parsing container.xml: {e}")
    
    # Fallback: search for .opf files
    for opf_file in work_dir.rglob("*.opf"):
        return opf_file
    
    return None

def convert_opf_to_epub2(opf_path):
    """Convert OPF file from EPUB 3 to EPUB 2 format"""
    print(f"Converting OPF file: {opf_path}")
    
    with open(opf_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update version to 2.0
    content = re.sub(r'version="3\.[0-9]+"', 'version="2.0"', content)
    
    # Update package element to EPUB 2.0.1 and remove xml:lang attribute
    content = re.sub(r'<package[^>]*>', 
                    '<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="eisbn" version="2.0">', 
                    content)
    
    # Remove EPUB 3 specific namespaces
    content = re.sub(r'\s*xmlns:epub="[^"]*"', '', content)
    
    # Remove EPUB 3 properties
    content = re.sub(r'\s*properties="[^"]*"', '', content)
    
    # Remove media-overlay attributes
    content = re.sub(r'\s*media-overlay="[^"]*"', '', content)
    
    # Fix media types - ensure XHTML files have correct media type
    # First, fix any XHTML files that were incorrectly set to NCX media type
    content = re.sub(
        r'(<item\s+[^>]*href="[^"]*\.xhtml"[^>]*?)media-type="application/x-dtbncx\+xml"',
        r'\1media-type="application/xhtml+xml"',
        content
    )
    
    # Convert nav document reference to NCX (only for actual nav files)
    content = re.sub(
        r'<item\s+([^>]*?)href="([^"]*nav[^"]*\.xhtml)"([^>]*?)media-type="application/xhtml\+xml"([^>]*?)properties="nav"([^>]*?)/>',
        lambda m: f'<item {m.group(1)}href="{m.group(2).replace("nav.xhtml", "toc.ncx")}" {m.group(3)}media-type="application/x-dtbncx+xml"{m.group(4)}{m.group(5)}/>'.replace('properties="nav"', ''),
        content
    )
    
    # Ensure NCX is referenced in spine
    if 'application/x-dtbncx+xml' in content and '<spine' in content:
        # Add toc attribute to spine if not present
        if 'toc=' not in content:
            # Find the NCX item id
            ncx_match = re.search(r'<item\s+[^>]*id="([^"]+)"[^>]*media-type="application/x-dtbncx\+xml"', content)
            if ncx_match:
                ncx_id = ncx_match.group(1)
                content = re.sub(r'<spine([^>]*?)>', f'<spine toc="{ncx_id}"\\1>', content)
    
    # Remove EPUB 3 specific metadata
    content = re.sub(r'<meta\s+property="[^"]*"[^>]*>[^<]*</meta>', '', content)
    content = re.sub(r'<meta\s+property="[^"]*"[^>]*/>', '', content)
    content = re.sub(r'<meta\s+id="[^"]*"\s+property="[^"]*"[^>]*>[^<]*</meta>', '', content)
    content = re.sub(r'<meta\s+id="[^"]*"\s+property="[^"]*"[^>]*/>', '', content)
    
    # Remove any remaining EPUB 3 meta elements with property attribute
    content = re.sub(r'<meta[^>]*property="[^"]*"[^>]*/?>', '', content)
    
    # Clean up empty lines
    content = re.sub(r'\n\s*\n', '\n', content)
    
    with open(opf_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("OPF file converted to EPUB 2 format")

def create_ncx_from_opf(opf_path, work_dir):
    """Create NCX file from OPF spine information"""
    print(f"Creating NCX from OPF spine: {opf_path}")
    
    # Extract title and identifier from OPF
    with open(opf_path, 'r', encoding='utf-8') as f:
        opf_content = f.read()
    
    title_match = re.search(r'<dc:title[^>]*>([^<]+)</dc:title>', opf_content)
    title = title_match.group(1) if title_match else "Unknown Title"
    
    # Extract unique identifier
    uid_match = re.search(r'<dc:identifier[^>]*>([^<]+)</dc:identifier>', opf_content)
    uid = uid_match.group(1) if uid_match else "unknown"
    
    # Extract navigation items from OPF spine
    nav_items = []
    
    print("Creating NCX from OPF spine...")
    spine_pattern = r'<itemref\s+idref="([^"]+)"'
    spine_matches = re.findall(spine_pattern, opf_content)
    
    for i, idref in enumerate(spine_matches, 1):
         # Find the corresponding item in manifest with more flexible pattern
         item_patterns = [
             f'<item\s+[^>]*id="{idref}"[^>]*href="([^"]+)"[^>]*media-type="application/xhtml\+xml"',
             f'<item\s+[^>]*href="([^"]+)"[^>]*id="{idref}"[^>]*media-type="application/xhtml\+xml"',
             f'<item\s+[^>]*id="{idref}"[^>]*href="([^"]+)"',
             f'<item\s+[^>]*href="([^"]+)"[^>]*id="{idref}"'
         ]
         
         href = None
         for pattern in item_patterns:
             item_match = re.search(pattern, opf_content)
             if item_match:
                 href = item_match.group(1)
                 break
         
         if href and href.endswith('.xhtml'):
              # Use the full relative path as it appears in the OPF for NCX references
              # This ensures the NCX references match the actual file locations
              
              # Try to get a better title from the file content
              file_path = work_dir / href
              chapter_title = f'Chapter {i}'
              
              if file_path.exists():
                  try:
                      with open(file_path, 'r', encoding='utf-8') as f:
                          file_content = f.read()
                          # Look for title in h1, h2, or title tags
                          title_match = re.search(r'<(?:h[1-2]|title)[^>]*>([^<]+)</(?:h[1-2]|title)>', file_content)
                          if title_match:
                              chapter_title = title_match.group(1).strip()
                  except:
                      pass  # Use default title if file reading fails
              
              nav_items.append({
                  'id': f'navPoint-{i}',
                  'playOrder': str(i),
                  'text': chapter_title,
                  'src': href  # Use full relative path as in OPF
              })
              print(f"Added nav item: {chapter_title} -> {href}")
    
    # Create NCX content
    ncx_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{uid}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle>
    <text>{title}</text>
  </docTitle>
  <navMap>
'''
    
    for item in nav_items:
        # Escape XML entities in text
        escaped_text = item['text'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        ncx_content += f'''    <navPoint id="{item['id']}" playOrder="{item['playOrder']}">
      <navLabel>
        <text>{escaped_text}</text>
      </navLabel>
      <content src="{item['src']}"/>
    </navPoint>
'''
    
    ncx_content += '''  </navMap>
</ncx>
'''
    
    # Write NCX file to the same directory as OPF
    ncx_path = opf_path.parent / "toc.ncx"
    with open(ncx_path, 'w', encoding='utf-8') as f:
        f.write(ncx_content)
    
    print(f"Created NCX file: {ncx_path}")
    return ncx_path

def convert_content_files_to_epub2(work_dir):
    """Convert XHTML content files to EPUB 2 compatibility"""
    print("Converting content files to EPUB 2 compatibility...")
    
    # Find all XHTML files
    for xhtml_file in work_dir.rglob("*.xhtml"):
        if xhtml_file.name == "nav.xhtml":  # Skip navigation document
            continue
            
        print(f"Processing: {xhtml_file}")
        
        with open(xhtml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove EPUB 3 specific attributes and elements
        content = remove_epub3_features(content)
        
        with open(xhtml_file, 'w', encoding='utf-8') as f:
            f.write(content)

def remove_epub3_features(content):
    """Remove EPUB 3 features that are not compatible with EPUB 2"""
    
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
    
    return content

def convert_epub3_to_epub2(epub_path):
    """Main function to convert EPUB 3 to EPUB 2"""
    epub_path = Path(epub_path)
    
    if not epub_path.exists():
        print(f"Error: EPUB file not found: {epub_path}")
        return None
    
    print(f"Converting EPUB 3 to EPUB 2: {epub_path}")
    
    # Create temporary working directory
    with tempfile.TemporaryDirectory() as temp_dir:
        work_dir = Path(temp_dir) / "epub_work"
        work_dir.mkdir()
        
        # Extract EPUB
        extract_epub(epub_path, work_dir)
        
        # Find OPF file
        opf_path = find_opf_file(work_dir)
        if not opf_path:
            print("Error: Could not find OPF file")
            return None
        
        # Find navigation document
        nav_path = None
        for xhtml_file in work_dir.rglob("*.xhtml"):
            with open(xhtml_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'epub:type="toc"' in content or 'nav.xhtml' in str(xhtml_file):
                    nav_path = xhtml_file
                    break
        
        # Convert OPF to EPUB 2
        convert_opf_to_epub2(opf_path)
        
        # Create NCX from OPF spine instead of nav document for better compatibility
        ncx_path = create_ncx_from_opf(opf_path, work_dir)
        
        # Update OPF to reference NCX
        with open(opf_path, 'r', encoding='utf-8') as f:
            opf_content = f.read()
        
        # Add NCX to manifest if not already present
        if 'toc.ncx' not in opf_content:
            # Find the manifest section and add NCX item
            manifest_end = opf_content.find('</manifest>')
            if manifest_end != -1:
                ncx_item = '<item href="toc.ncx" id="ncx" media-type="application/x-dtbncx+xml"/>\n'
                opf_content = opf_content[:manifest_end] + ncx_item + opf_content[manifest_end:]
        
        # Remove any nav document references
        if nav_path:
            nav_relative_path = str(nav_path.relative_to(work_dir)).replace('\\', '/')
            opf_content = re.sub(
                f'<item\s+[^>]*href="{re.escape(nav_relative_path)}"[^>]*/>\n?',
                '',
                opf_content
            )
            
            with open(opf_path, 'w', encoding='utf-8') as f:
                f.write(opf_content)
            
            # Remove the original navigation document
            nav_path.unlink()
        
        # Convert content files
        convert_content_files_to_epub2(work_dir)
        
        # Create output EPUB
        output_path = epub_path.parent / f"{epub_path.stem}_epub2.epub"
        create_epub_from_directory(str(work_dir), str(output_path))
        
        return output_path

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python convert_epub3_to_epub2.py <epub_file>")
        sys.exit(1)
    
    epub_file = sys.argv[1]
    result = convert_epub3_to_epub2(epub_file)
    
    if result:
        print(f"\n✅ Successfully converted to EPUB 2: {result}")
    else:
        print("\n❌ Conversion failed")
        sys.exit(1)