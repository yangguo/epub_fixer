#!/usr/bin/env python3
import zipfile
import os

def debug_meta_tag():
    # Extract and examine the meta tag in detail
    with zipfile.ZipFile('doing1.epub', 'r') as epub:
        epub.extractall('debug3_epub')
    
    file_path = 'debug3_epub/OEBPS/cover.xhtml'
    
    with open(file_path, 'rb') as f:
        content = f.read()
    
    lines = content.split(b'\n')
    if len(lines) > 5:
        line6 = lines[5]  # Line 6 (0-indexed line 5)
        print(f"Line 6 raw bytes: {line6}")
        print(f"Line 6 length: {len(line6)}")
        
        # Find the meta tag
        meta_start = line6.find(b'<meta')
        if meta_start != -1:
            meta_end = line6.find(b'/>', meta_start)
            if meta_end != -1:
                meta_tag = line6[meta_start:meta_end+2]
                print(f"Meta tag: {meta_tag}")
                print(f"Meta tag decoded: {meta_tag.decode('utf-8', errors='replace')}")
                
                # Check each character in the meta tag
                print("\nCharacter by character analysis:")
                for i, byte in enumerate(meta_tag):
                    char = chr(byte) if 32 <= byte <= 126 else f'\\x{byte:02x}'
                    print(f"Position {meta_start + i + 1}: {byte:3d} ({char})")
                    
                # Look for the charset part specifically
                charset_pos = meta_tag.find(b'charset=')
                if charset_pos != -1:
                    charset_section = meta_tag[charset_pos:charset_pos+20]
                    print(f"\nCharset section: {charset_section}")
                    print(f"Charset section decoded: {charset_section.decode('utf-8', errors='replace')}")
                    
                    # Check for double quotes or other issues
                    quote_count = charset_section.count(b'"')
                    print(f"Quote count in charset section: {quote_count}")
                    
                    # Check the specific area around position 68
                    global_pos_68 = 67  # 0-indexed position 67 = 1-indexed position 68
                    if global_pos_68 < len(line6):
                        print(f"\nCharacter at global position 68: {line6[global_pos_68]} ({chr(line6[global_pos_68]) if 32 <= line6[global_pos_68] <= 126 else f'\\x{line6[global_pos_68]:02x}'})")
                        print(f"Context around position 68: {line6[global_pos_68-5:global_pos_68+5]}")

if __name__ == '__main__':
    debug_meta_tag()