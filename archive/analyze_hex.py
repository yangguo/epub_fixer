#!/usr/bin/env python3

# Read the problematic line and analyze the hex pattern
with open('debug2_epub/OEBPS/cover.xhtml', 'rb') as f:
    lines = f.readlines()
    line6 = lines[5]  # Line 6 (0-indexed)

print("Line 6 content:")
print(repr(line6.decode()))
print("\nLine 6 hex:")
print(line6.hex())

# Find the charset part
hex_str = line6.hex()
charset_pos = hex_str.find('636861727365743d22')  # "charset="
if charset_pos != -1:
    print(f"\nCharset found at hex position: {charset_pos}")
    # Extract charset="utf-8"/>
    charset_section = hex_str[charset_pos:charset_pos+40]  # Get more context
    print(f"Charset section hex: {charset_section}")
    
    # Convert back to string
    charset_bytes = bytes.fromhex(charset_section)
    print(f"Charset section string: {repr(charset_bytes.decode())}")
    
    # Look specifically for the quote pattern around utf-8
    utf8_pos = hex_str.find('7574662d38')  # "utf-8"
    if utf8_pos != -1:
        print(f"\nUTF-8 found at hex position: {utf8_pos}")
        # Get 10 characters before and after utf-8
        context = hex_str[utf8_pos-20:utf8_pos+30]
        print(f"Context around utf-8: {context}")
        context_bytes = bytes.fromhex(context)
        print(f"Context decoded: {repr(context_bytes.decode())}")
        
        # Check for double quotes
        before_utf8 = hex_str[utf8_pos-4:utf8_pos]
        after_utf8 = hex_str[utf8_pos+10:utf8_pos+14]
        print(f"\nBefore utf-8: {before_utf8} = {repr(bytes.fromhex(before_utf8).decode())}")
        print(f"After utf-8: {after_utf8} = {repr(bytes.fromhex(after_utf8).decode())}")

# Check character at position 66 (1-indexed, so 65 in 0-indexed)
print(f"\nCharacter at position 66: {repr(line6[65:66].decode()) if len(line6) > 65 else 'Not found'}")
print(f"Characters 60-70: {repr(line6[59:69].decode()) if len(line6) > 59 else 'Not enough chars'}")