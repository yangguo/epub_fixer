#!/usr/bin/env python3
import zipfile
import re

def check_page_anchors():
    with zipfile.ZipFile('doing1.epub', 'r') as epub:
        # Check chapter01.xhtml for page anchors
        content = epub.read('OEBPS/chapter01.xhtml').decode('utf-8')
        
        # Look for page anchors like id="page7", id="page8", etc.
        page_anchors = re.findall(r'id="page\d+"', content)
        print(f"Found {len(page_anchors)} page anchors in chapter01.xhtml:")
        if page_anchors:
            print(page_anchors[:10])  # Show first 10
        else:
            print("No page anchors found")
        
        # Also check for any anchor tags with class="calibre6"
        calibre_anchors = re.findall(r'<a[^>]*class="calibre6"[^>]*>', content)
        print(f"\nFound {len(calibre_anchors)} calibre6 anchors in chapter01.xhtml:")
        if calibre_anchors:
            print(calibre_anchors[:5])  # Show first 5
        
        # Check what the actual structure looks like around line 27 (where first error occurs)
        lines = content.split('\n')
        if len(lines) > 30:
            print("\nContent around lines 25-30:")
            for i in range(24, min(31, len(lines))):
                print(f"{i+1}: {lines[i][:100]}..." if len(lines[i]) > 100 else f"{i+1}: {lines[i]}")

if __name__ == '__main__':
    check_page_anchors()