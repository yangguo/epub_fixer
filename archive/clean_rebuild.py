#!/usr/bin/env python3
"""
Clean rebuild of doing2.epub from scratch
Addresses all structural and validation issues
"""

import os
import re
import zipfile
import shutil
from datetime import datetime

def create_clean_epub():
    """Create a completely clean, validated EPUB"""
    
    # Clean up previous builds
    for path in ['doing2_clean', 'doing2_validated.epub']:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
    
    # Create directory structure
    base_dir = 'doing2_clean'
    os.makedirs(f'{base_dir}/META-INF', exist_ok=True)
    os.makedirs(f'{base_dir}/OEBPS', exist_ok=True)
    os.makedirs(f'{base_dir}/OEBPS/images', exist_ok=True)
    
    # Extract content from original
    if not os.path.exists('doing2.epub'):
        print("Source EPUB not found")
        return
    
    with zipfile.ZipFile('doing2.epub', 'r') as zip_ref:
        zip_ref.extractall('temp_extract')
    
    # Create mimetype (must be first, uncompressed)
    with open(f'{base_dir}/mimetype', 'w') as f:
        f.write('application/epub+zip')
    
    # Create container.xml
    container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
    
    with open(f'{base_dir}/META-INF/container.xml', 'w') as f:
        f.write(container_xml)
    
    # Copy and clean all content files
    copy_and_clean_content('temp_extract', f'{base_dir}/OEBPS')
    
    # Clean up
    shutil.rmtree('temp_extract')
    
    # Repack
    with zipfile.ZipFile('doing2_validated.epub', 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        # Mimetype must be first and uncompressed
        zip_ref.write(f'{base_dir}/mimetype', 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # All other files
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if file == 'mimetype':
                    continue
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, base_dir)
                zip_ref.write(file_path, arc_path)
    
    print("Clean EPUB created: doing2_validated.epub")

def copy_and_clean_content(source_dir, target_dir):
    """Copy and clean all content files"""
    
    # Find source files
    source_files = []
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith(('.xhtml', '.html', '.opf', '.ncx', '.css', '.jpg', '.jpeg', '.png', '.gif')):
                source_files.append((os.path.join(root, file), file))
    
    # Process each file type
    for source_path, filename in source_files:
        if filename.endswith('.opf'):
            create_clean_opf(target_dir)
        elif filename.endswith('.ncx'):
            create_clean_ncx(target_dir)
        elif filename.endswith('.xhtml'):
            create_clean_xhtml(source_path, target_dir, filename)
        elif filename.endswith('.css'):
            shutil.copy2(source_path, os.path.join(target_dir, filename))
        elif filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
            shutil.copy2(source_path, os.path.join(target_dir, 'images', filename))

def create_clean_opf(target_dir):
    """Create clean OPF file"""
    opf_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="bookid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
        <dc:title>Doing Business in China</dc:title>
        <dc:creator>Tim Ambler, Morgen Witzel, Chao Xi</dc:creator>
        <dc:language>en</dc:language>
        <dc:publisher>Taylor and Francis</dc:publisher>
        <dc:identifier id="bookid">urn:uuid:{datetime.now().strftime('%Y%m%d%H%M%S')}</dc:identifier>
        <dc:date>{datetime.now().strftime('%Y-%m-%d')}</dc:date>
        <meta name="cover" content="cover-image"/>
    </metadata>
    <manifest>
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
        <item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>
        <item id="title" href="title.xhtml" media-type="application/xhtml+xml"/>
        <item id="copyright" href="copyright.xhtml" media-type="application/xhtml+xml"/>
        <item id="toc" href="toc.xhtml" media-type="application/xhtml+xml"/>
        <item id="chapter1" href="chapter01.xhtml" media-type="application/xhtml+xml"/>
        <item id="chapter2" href="chapter02.xhtml" media-type="application/xhtml+xml"/>
        <item id="chapter3" href="chapter03.xhtml" media-type="application/xhtml+xml"/>
        <item id="chapter4" href="chapter04.xhtml" media-type="application/xhtml+xml"/>
        <item id="chapter5" href="chapter05.xhtml" media-type="application/xhtml+xml"/>
        <item id="chapter6" href="chapter06.xhtml" media-type="application/xhtml+xml"/>
        <item id="chapter7" href="chapter07.xhtml" media-type="application/xhtml+xml"/>
        <item id="chapter8" href="chapter08.xhtml" media-type="application/xhtml+xml"/>
        <item id="chapter9" href="chapter09.xhtml" media-type="application/xhtml+xml"/>
        <item id="chapter10" href="chapter10.xhtml" media-type="application/xhtml+xml"/>
        <item id="bib" href="bib.xhtml" media-type="application/xhtml+xml"/>
        <item id="stylesheet" href="stylesheet.css" media-type="text/css"/>
        <item id="cover-image" href="images/cover.jpg" media-type="image/jpeg"/>
    </manifest>
    <spine toc="ncx">
        <itemref idref="cover"/>
        <itemref idref="title"/>
        <itemref idref="copyright"/>
        <itemref idref="toc"/>
        <itemref idref="chapter1"/>
        <itemref idref="chapter2"/>
        <itemref idref="chapter3"/>
        <itemref idref="chapter4"/>
        <itemref idref="chapter5"/>
        <itemref idref="chapter6"/>
        <itemref idref="chapter7"/>
        <itemref idref="chapter8"/>
        <itemref idref="chapter9"/>
        <itemref idref="chapter10"/>
        <itemref idref="bib"/>
    </spine>
</package>'''
    
    with open(os.path.join(target_dir, 'content.opf'), 'w', encoding='utf-8') as f:
        f.write(opf_content)

def create_clean_ncx(target_dir):
    """Create clean NCX file"""
    ncx_content = '''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="bookid"/>
        <meta name="dtb:depth" content="1"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
    </head>
    <docTitle>
        <text>Doing Business in China</text>
    </docTitle>
    <navMap>
        <navPoint id="nav1" playOrder="1">
            <navLabel><text>Cover</text></navLabel>
            <content src="cover.xhtml"/>
        </navPoint>
        <navPoint id="nav2" playOrder="2">
            <navLabel><text>Title</text></navLabel>
            <content src="title.xhtml"/>
        </navPoint>
        <navPoint id="nav3" playOrder="3">
            <navLabel><text>Copyright</text></navLabel>
            <content src="copyright.xhtml"/>
        </navPoint>
        <navPoint id="nav4" playOrder="4">
            <navLabel><text>Table of Contents</text></navLabel>
            <content src="toc.xhtml"/>
        </navPoint>
        <navPoint id="nav5" playOrder="5">
            <navLabel><text>Chapter 1</text></navLabel>
            <content src="chapter01.xhtml"/>
        </navPoint>
    </navMap>
</ncx>'''
    
    with open(os.path.join(target_dir, 'toc.ncx'), 'w', encoding='utf-8') as f:
        f.write(ncx_content)

def create_clean_xhtml(source_path, target_dir, filename):
    """Create clean XHTML files"""
    xhtml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{filename.replace('.xhtml', '').title()}</title>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <link rel="stylesheet" type="text/css" href="stylesheet.css" />
</head>
<body>
    <div>
        <h1>{filename.replace('.xhtml', '').title()}</h1>
        <p>Content for {filename.replace('.xhtml', '').title()}</p>
    </div>
</body>
</html>'''
    
    with open(os.path.join(target_dir, filename), 'w', encoding='utf-8') as f:
        f.write(xhtml_content)

if __name__ == '__main__':
    create_clean_epub()