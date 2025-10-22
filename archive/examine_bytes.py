#!/usr/bin/env python3

# Read the problematic line and examine each byte
with open('debug2_epub/OEBPS/cover.xhtml', 'rb') as f:
    lines = f.readlines()
    line6 = lines[5]  # Line 6 (0-indexed)

print("Byte-by-byte analysis of line 6:")
print("Pos: Hex  Char")
print("-" * 15)

for i, byte in enumerate(line6):
    char = chr(byte) if 32 <= byte <= 126 else f'\\x{byte:02x}'
    print(f"{i:2d}: {byte:02x}   {char}")
    
print(f"\nTotal length: {len(line6)} bytes")
print(f"Character at position 65 (0-indexed): {line6[65]:02x} = {repr(chr(line6[65]))}")
print(f"Character at position 66 (1-indexed): {line6[65]:02x} = {repr(chr(line6[65]))}")

# Look for the meta tag structure
line_str = line6.decode()
print(f"\nLine as string: {repr(line_str)}")

# Check if there are any issues with the meta tag
import re
meta_pattern = r'<meta\s+[^>]*>'
match = re.search(meta_pattern, line_str)
if match:
    print(f"\nMeta tag found: {repr(match.group())}")
    print(f"Meta tag starts at position: {match.start()}")
    print(f"Meta tag ends at position: {match.end()}")
else:
    print("\nNo complete meta tag found!")
    
# Check for self-closing tag
self_closing_pattern = r'<meta\s+[^>]*/\s*>'
match2 = re.search(self_closing_pattern, line_str)
if match2:
    print(f"\nSelf-closing meta tag: {repr(match2.group())}")
else:
    print("\nMeta tag is not properly self-closed!")