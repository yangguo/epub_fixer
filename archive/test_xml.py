#!/usr/bin/env python3
import xml.etree.ElementTree as ET

# Test different meta tag formats
test_cases = [
    '<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>',
    '<meta http-equiv="Content-Type" content="text/html; charset=\"utf-8\""/>',
    '<meta http-equiv="Content-Type" content="text/html; charset=&quot;utf-8&quot;"/>'
]

for i, test in enumerate(test_cases, 1):
    print(f"Test case {i}: {test}")
    try:
        ET.fromstring(test)
        print("  VALID XML")
    except Exception as e:
        print(f"  INVALID XML: {e}")
    print()