#!/usr/bin/env python3
from pathlib import Path

# Search for files with the bad charset pattern
bad_hex = '636861727365743d227574662d3822222f3e'  # charset="utf-8""/>
found_files = []

for file_path in Path('debug2_epub').rglob('*.xhtml'):
    try:
        content = file_path.read_bytes().hex()
        if bad_hex in content:
            found_files.append(str(file_path))
            print(f"Found bad pattern in: {file_path}")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

if not found_files:
    print("No files found with the bad charset pattern.")
    print("Let me check what the actual pattern looks like...")
    
    # Check the first file to see what pattern exists
    first_file = next(Path('debug2_epub').rglob('*.xhtml'), None)
    if first_file:
        content = first_file.read_bytes()
        start = content.find(b'charset')
        if start >= 0:
            pattern_bytes = content[start:start+20]
            print(f"Actual pattern in {first_file.name}: {pattern_bytes.hex()}")
            print(f"String representation: {repr(pattern_bytes)}")
else:
    print(f"Found {len(found_files)} files with bad pattern.")